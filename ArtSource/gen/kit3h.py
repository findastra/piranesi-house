"""v3 Stormscape: the Colossus hall's vault and dome broken open to the sky (a 6.6 m hole) so the spiral stair can rise through."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kit3 as K3
from kit3 import K, reset
reset()
ob = K.make_vestibule_core(hole=6.6, name='Vest_Core_Open'); K.export_bytes(ob, 'Vest_Core_Open')
K3.vest_dome(rtop=7.2, lantern=False, name='Vest_Dome_Open')
print('kit3h done')
