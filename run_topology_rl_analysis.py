#!/usr/bin/env python3
"""
Run Topology RL Impact Analysis (10-router system)
"""

import os
import sys

# Add to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Change working directory
os.chdir(script_dir)

# Now run
if __name__ == "__main__":
    topology_dir = os.path.join(script_dir, 'Topology_RL_Impact')
    os.chdir(topology_dir)
    if topology_dir not in sys.path:
        sys.path.insert(0, topology_dir)
    from topology_rl_impact_fixed import main
    main()
