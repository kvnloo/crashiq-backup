"""Surrogate safety: traffic conflicts (near-misses) found in vehicle trajectories (#484).

Method credit: FHWA's Surrogate Safety Assessment Model (SSAM), as published in FHWA-HRT-08-051 ("Surrogate Safety
Assessment Model and Validation: Final Report", 2008, Ch. 2) and the SSAM user manual FHWA-HRT-08-050, with the
trajectory file layout from the public SSAM File Format specs v1.04 (Siemens, 2004) and v3.0 (2017).

This is an independent, clean-room implementation of that published method. It is NOT FHWA's SSAM software, contains
none of SSAM's source code, and its results are CrashIQ's own.
"""

from .conflicts import find_conflicts
from .trj import Trj, Veh, read_trajectory_csv, read_trj, write_trj

__all__ = ["Trj", "Veh", "find_conflicts", "read_trajectory_csv", "read_trj", "write_trj"]
