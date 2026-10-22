# SG5 Drowsiness Decision and Alert Logic

Subgroup: Rafed Aftab and Filza Umar, G1-D2.

SG-5 consumes temporal eye, yawn and fatigue evidence from SG-4, chooses a driver state, and requests an alert action from SG-6.

The Week 5 implementation, retained Week 4 baseline, two-rule comparison, fixed mock data and results are in [week_5](week_5/README.md).

```powershell
cd module_5/week_5
python demo.py
python compare.py
python -m unittest -v
```

Requires Python 3.10 or later; no third-party packages. See [V1 interface](week_5/INTERFACE.md) and [viva guide](week_5/VIVA_GUIDE.md).

The current evidence is based on simulated temporal inputs. Real-driver validation, agreement of the local V1 contract with SG-4/SG-6, and Jetson profiling remain future integration work.
