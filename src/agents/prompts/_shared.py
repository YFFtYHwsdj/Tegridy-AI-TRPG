EFFECT_TYPES_REFERENCE = """
效果类型决定了行动的性质。每种效果类型通过一个具体的"操作（operation）"来实现。

=== 操作类型总览 ===

操作分为两大类：机械效果（产生代码可追踪的标签或状态变化）和叙事效果（纯文本输出）。

【机械效果操作】

• inflict_status — 给目标施加一个指定等级的新状态
  花费: 1力量/等级
  对应效果类型: attack, influence, disrupt, enhance, advance
  重要：如果你给一个**已经存在**的状态施加 inflict_status，它会按溢出规则累加等级。

• nudge_status — 将目标的某个已有状态提升1级
  花费: 1力量
  对应效果类型: attack, influence, disrupt, enhance, advance
  与 inflict_status 的区别：
    - inflict_status 的 tier 是绝对值（"给3级受伤"），nudge_status 是增量（"受伤+1级"）
    - 如果状态不存在，nudge_status 自动创建为1级
    - 如果状态已存在，nudge_status 在当前等级基础上+1
    - **推进极限时优先用 nudge_status**——当你只需提升1级就能到达极限时，1力量刚好够

• reduce_status — 降低目标的某个已有状态的等级
  花费: 1力量/每降低1级
  对应效果类型: restore, set_back

• add_story_tag — 给目标添加一个故事标签
  花费: 2力量/标签（或1力量如果标记为single_use）
  对应效果类型: bestow, create

• scratch_story_tag — 移除目标的一个已有故事标签
  花费: 2力量/标签（或1力量如果是single_use）
  对应效果类型: weaken

【叙事效果操作】

• discover — 发现场景中的一个有价值细节
  花费: 1力量
  对应效果类型: discover

• extra_feat — 额外壮举
  花费: 1力量（仅在至少1力量已用于行动主体后才可使用）
  对应效果类型: extra_feat

=== 状态叠加（溢出）机制 ===
当挑战已有某个状态时，再次施加同类型状态会叠加而非替换：
  - 如果状态不存在 → 勾选对应等级的盒子，current_tier = 施加的等级
  - 如果状态已存在:
    - 用 inflict_status tier=X: 勾选盒子X。若X已勾选则溢出到X+1（直到找到空盒）
    - 用 nudge_status: 勾选 current_tier+1 的盒子（若已勾选则继续+1）
  - 状态的真实等级 = 已勾选的最大盒子编号

【推进极限的关键规则】
如果你想推进挑战的极限（例如"说服或威胁"），先看挑战的当前状态：
  - 状态「愿意交易」当前2级，极限需要3级 → 需要+1级
  - 可用力量=1 → 用 nudge_status（1力量升1级，恰好到达极限）
  - 可用力量≥2 → 可用 inflict_status tier=2（盒子2有→溢出到3）或 nudge_status

=== 效果类型与操作的对应关系 ===

针对对手或目标：
  attack → inflict_status 或 nudge_status（有害状态）
  influence → inflict_status 或 nudge_status（强制状态）
  disrupt → inflict_status 或 nudge_status（阻碍状态）
  weaken → scratch_story_tag 或 reduce_status

针对自身或盟友：
  bestow → add_story_tag
  enhance → inflict_status 或 nudge_status（有益状态）
  restore → reduce_status

针对过程：
  advance → inflict_status 或 nudge_status（进度状态）
  set_back → reduce_status

其他：
  discover → discover
  create → add_story_tag
  extra_feat → extra_feat

=== 力量花费速查 ===
inflict_status: 1/等级
nudge_status: 1
reduce_status: 1/每降低1级
add_story_tag: 2/标签（1若single_use）
scratch_story_tag: 2/标签（1若single_use）
discover: 1
extra_feat: 1（需至少1力量已用于主体）"""
