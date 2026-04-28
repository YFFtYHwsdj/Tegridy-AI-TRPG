"""快速回归测试 —— Character.is_incapacitated() 判定逻辑验证。

测试四种场景：
    1. 任意状态 tier 6 → incapacitated
    2. 特定状态名 tier 1+ → incapacitated
    3. 低 tier 普通状态 → 非 incapacitated
    4. 无状态 → 非 incapacitated
"""

import sys

sys.path.insert(0, "/Users/tegridy/Git Programs/Tegridy-AI-TRPG")
from src.models import Character, Status

results = []
c = Character(name="T")
c.statuses["受伤"] = Status(name="受伤", current_tier=6, ticked_boxes={6})
results.append(("tier6", c.is_incapacitated()))

c2 = Character(name="T")
c2.statuses["被打晕"] = Status(name="被打晕", current_tier=2, ticked_boxes={1, 2})
results.append(("explicit_name", c2.is_incapacitated()))

c3 = Character(name="T")
c3.statuses["受伤"] = Status(name="受伤", current_tier=3, ticked_boxes={1, 2, 3})
results.append(("low_tier", not c3.is_incapacitated()))

c4 = Character(name="T")
results.append(("no_statuses", not c4.is_incapacitated()))

for name, passed in results:
    status = "PASS" if passed else "FAIL"
    print(f"{status}: {name}")
all_pass = all(r[1] for r in results)
if all_pass:
    print("ALL 4 TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
