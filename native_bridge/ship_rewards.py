# /// script
# dependencies = ["pymhf[gui]==0.2.5"]
# requires-python = ">=3.12,<3.13"
# [tool.pymhf]
# exe = "NMS.exe"
# start_exe = false
# start_paused = false
# interactive_console = false
# [tool.pymhf.gui]
# shown = false
# [tool.pymhf.logging]
# log_dir = "../runtime/native-ship-bridge"
# log_level = "info"
# ///
"""Experimental optional pyMHF mod. Not injected by the menu automatically.

An extra native reward is called only inside a real non-peek reward callback.
The ordinary reward and its arguments/result are never replaced.
"""
import ctypes as C
import json
import os
from pathlib import Path
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nmsmenu.runtime_ship import BRIDGE, REWARD_RVA, atomic_json, capture, validate_request, verify_binary
from nmsmenu.live import BUILD_HASH, EXE, LiveBackend
from nmsmenu.winmem import ProcessMemory

def verify_host():
    # Called by mod construction before the loader registers this mod's hooks.
    host_path = C.create_unicode_buffer(32768)
    if not C.windll.kernel32.GetModuleFileNameW(None, host_path, len(host_path)):
        raise RuntimeError('Cannot identify native host.')
    if Path(host_path.value).resolve() != EXE.resolve():
        raise RuntimeError('Load this mod only in the established GOG NMS.exe.')
    verify_binary(host_path.value)

from pymhf import Mod, load_mod_file
from pymhf.core.hooking import Structure, function_hook


class RewardManager(Structure):
    @function_hook(offset=REWARD_RVA)
    def GiveShipReward(self, this: C.c_uint64, reward: C.c_void_p, mission: C.c_void_p,
                      seed: C.c_void_p, peek: C.c_bool, show: C.c_bool,
                      count: C.c_void_p, silent: C.c_bool, inventory: C.c_int32,
                      mining: C.c_bool) -> C.c_uint64:
        ...


class NativeShipRewards(Mod):
    __author__ = 'NMS Menu'
    __description__ = 'Experimental native ship rewards; explicit menu request required.'
    __version__ = '0.1.0'

    def __init__(self):
        verify_host()
        super().__init__()
        self.nonce = uuid.uuid4().hex
        self.inside = False
        self.last_result = None
        self.last_dispatch = 0.0
        self.attempted = False
        self.live = LiveBackend()
        self.live.memory = ProcessMemory(EXE, writable=False)
        if self.live.memory.pid != os.getpid():
            raise RuntimeError('Native bridge must read its own game process.')
        BRIDGE.mkdir(parents=True, exist_ok=True)
        atomic_json(BRIDGE / 'owner.json', {'nonce': self.nonce, 'pid': os.getpid()})
        threading.Thread(target=self.heartbeat, daemon=True).start()

    def owns_bridge(self):
        try:
            return json.loads((BRIDGE / 'owner.json').read_text())['nonce'] == self.nonce
        except (OSError, ValueError, KeyError):
            return False

    def heartbeat(self):
        while self.live.memory.alive() and self.owns_bridge():
            try:
                state = capture(self.live)
            except Exception as exc:
                state = {'loaded': False, 'offline': False, 'error': str(exc)}
            try:
                atomic_json(BRIDGE / 'status.json', {**state, 'nonce': self.nonce,
                    'timestamp': time.time(), 'build_hash': BUILD_HASH, 'pid': os.getpid(),
                    'accepting': not self.attempted,
                    'last_result': self.last_result, 'experimental': True})
            except OSError:
                pass
            time.sleep(1)

    @RewardManager.GiveShipReward.after
    def after_reward(self, this, reward, mission, seed, peek, show, count, silent, inventory, mining):
        # Borrow `this` only for this callback; never store/call it from a worker.
        # No replacement return value: pyMHF retains the ordinary native result.
        if self.inside or self.attempted or peek or not seed or not self.owns_bridge() or time.monotonic() - self.last_dispatch < 5:
            return
        pending = BRIDGE / 'request.json'
        if not pending.is_file():
            return
        claimed = BRIDGE / ('claimed-' + uuid.uuid4().hex + '.json')
        try:
            pending.rename(claimed)  # durable at-most-once claim, even after crash
        except OSError:
            return
        request = {}
        try:
            request = json.loads(claimed.read_text(encoding='utf-8'))
            state = capture(self.live)
            validate_request(request, state, self.nonce)
            # Separate argument storage; don't change the normal reward's mission,
            # output count, seed buffer, or ID. Native code owns ship construction.
            reward_id = C.create_string_buffer(request['reward'].encode('ascii'), 16)
            mission_id = C.create_string_buffer(16)
            seed_copy = C.create_string_buffer(self.live.memory.read(int(seed), 16), 16)
            output_count = C.c_uint64()
            self.inside = True
            self.attempted = True  # one native attempt per attachment, never auto-retry
            self.last_dispatch = time.monotonic()
            manager = RewardManager.from_address(int(this))
            result = manager.GiveShipReward(C.addressof(reward_id), C.addressof(mission_id),
                C.addressof(seed_copy), False, True, C.addressof(output_count), False, -1, False)
            self.last_result = {'id': request['id'], 'state': 'dispatched',
                'reward': request['reward'], 'native_result': result,
                'note': 'Delivery/claim UI may open; ownership has not been confirmed.'}
        except Exception as exc:
            self.last_result = {'id': request.get('id') if isinstance(request, dict) else None,
                                'state': 'rejected', 'error': str(exc)}
        finally:
            self.inside = False
            try:
                atomic_json(claimed.with_suffix('.result.json'), self.last_result)
            except OSError:
                pass  # claimed request remains durable; never retry a native call


if __name__ == '__main__':
    load_mod_file(__file__)
