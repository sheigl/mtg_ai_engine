import re, pathlib
p = pathlib.Path("/home/sheigl/code/mtg_ai_engine/tests/engine/test_crew_integration.py")
text = p.read_text()
tests = re.findall(r"^\s*def (test_\w+)", text, re.MULTILINE)
print("COUNT def test_:", len(tests))
for t in tests: print("  -", t)
