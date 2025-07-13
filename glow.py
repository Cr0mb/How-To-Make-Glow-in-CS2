import struct
import time
import random
from pymem import Pymem

class Offsets:
    dwLocalPlayerPawn = 25526480
    dwEntityList = 27280608
    m_iTeamNum = 995
    m_hPlayerPawn = 2084
    m_lifeState = 840
    m_Glow = 3072
    m_glowColorOverride = 64
    m_bGlowing = 81
    m_iGlowType = 48
    
class CS2GlowManager:
    def __init__(self, process_name="cs2.exe", module_name="client.dll"):
        self.pm = Pymem(process_name)
        self.client_base = next((m.lpBaseOfDll for m in self.pm.list_modules() if m.name.lower() == module_name.lower()), None)
        if not self.client_base:
            raise Exception("Failed to find client.dll module base.")

    def _read(self, addr, fmt):
        size = struct.calcsize(fmt)
        data = self.pm.read_bytes(addr, size)
        return struct.unpack(fmt, data)[0]
        
    def _write_u(self, addr, val):
        self.pm.write_bytes(addr, struct.pack("I", val), 4)
        
    def _to_argb(self, r, g, b, a):
        clamp = lambda x: max(0, min(1, x))
        r, g, b, a = [int(clamp(c) * 255) for c in (r, g, b, a)]
        return (a << 24) | (r << 16) | (g << 8) | b
        
    def _get_local_team(self):
        local_pawn = self._read(self.client_base + Offsets.dwLocalPlayerPawn, "Q")
        return None if local_pawn == 0 else self._read(local_pawn + Offsets.m_iTeamNum, "i")
        
        
    def update_glow(self):
        local = self._read(self.client_base + Offsets.dwLocalPlayerPawn, "Q")
        entity_list = self._read(self.client_base + Offsets.dwEntityList, "Q")
        team_local = self._get_local_team()
        if not local or not entity_list or team_local is None:
            return
            
        for i in range(64):
            entry = self._read(entity_list + 0x10, "Q")
            if not entry:
                continue
                
            controller = self._read(entry + i * 0x78, "Q")
            if not controller:
                continue
                
            pawn_handle = self._read(controller + Offsets.m_hPlayerPawn, "i")
            if not pawn_handle:
                continue
                
            entry2 = self._read(entity_list + 0x8 * ((pawn_handle & 0x7FFF) >> 9) + 0x10, "Q")
            if not entry2:
                continue
            
            pawn = self._read(entry2 + 0x78 * (pawn_handle & 0x1FF), "Q")
            if not pawn or pawn == local:
                continue
                
            is_team = self._read(pawn + Offsets.m_iTeamNum, "i") == team_local
            
            color = (1, 0, 0, 1) if is_team else (0, 0, 1, 1)
            
            glow = pawn + Offsets.m_Glow
            self._write_u(glow + Offsets.m_bGlowing, 1)
            self._write_u(glow + Offsets.m_iGlowType, 2)
            self._write_u(glow + Offsets.m_glowColorOverride, self._to_argb(*color))
            
    def run(self):
        try:
            while True:
                self.update_glow()
                time.sleep(0.01 + random.uniform(0, 0.005))
        except KeyboardInterrupt:
            print("Exiting..")
            self.pm.close_process()
            
if __name__ == "__main__":
    CS2GlowManager().run()