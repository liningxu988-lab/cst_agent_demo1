"""
Test CST COM interface available methods
"""

import win32com.client

print("=" * 60)
print("Testing CST COM Interface")
print("=" * 60)

try:
    # Connect to CST
    cst = win32com.client.Dispatch("CSTStudio.Application")
    print("[OK] Connected to CSTStudio.Application")
    print("  Type:", type(cst))

    # Check available methods
    print("\nChecking available methods and properties...")

    # Try different project access methods
    methods_to_try = [
        ("GetActiveProject", lambda: cst.GetActiveProject()),
        ("ActiveProject", lambda: cst.ActiveProject),
        ("Project", lambda: cst.Project),
        ("GetProject", lambda: cst.GetProject()),
    ]

    for method_name, method_call in methods_to_try:
        try:
            result = method_call()
            print("  [OK]", method_name, ":", result)
            if result:
                try:
                    path = result.GetProjectPath()
                    print("    Project path:", path)
                except:
                    pass
        except Exception as e:
            print("  [FAIL]", method_name, ":", e)

    # Check Projects collection
    try:
        projects = cst.Projects
        print("\n[OK] Projects collection:", projects)
        print("  Count:", projects.Count())
        for i in range(projects.Count()):
            try:
                proj = projects.Item(i)
                print("  Project", i, ":", proj.GetProjectPath())
            except Exception as e:
                print("  Project", i, ": cannot get path (", e, ")")
    except Exception as e:
        print("\n[FAIL] Projects collection:", e)

    # Try OpenProject different ways
    print("\nTesting OpenProject...")
    test_paths = [
        r"E:\code\cst_agent_demo\templates\antenna_template",
        r"E:\code\cst_agent_demo\templates\antenna_template.cst",
    ]

    for path in test_paths:
        try:
            print("\n  Trying:", path)
            proj = cst.OpenProject(path)
            if proj:
                print("    [OK] Success!")
                print("    Project path:", proj.GetProjectPath())
                break
        except Exception as e:
            print("    [FAIL]", e)

    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
