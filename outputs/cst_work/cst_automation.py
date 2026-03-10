"""
CST Automation Script
Run this in CST's Python environment
"""

import cst

# Get current project
proj = cst.project

# Update parameters
proj.set_parameter("_comment", CST 自动设计参数示例文件)
proj.set_parameter("project_path", templates/antenna_template)
proj.set_parameter("patch_length", 12.0)
proj.set_parameter("patch_width", 10.0)

# Rebuild
proj.rebuild()

# Run simulation
solver = proj.get_solver()
solver.run()

print("Simulation completed!")
