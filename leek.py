"""🥬 韭菜的自我修养 · 给AI玩的A股模拟器 v3.0

【给 AI 玩家的说明】
你是 A 股市场里的一棵韭菜。1000 块起步，13只股票，4大板块，牛熊周期。
升到交易员15级后解锁 💼基金经理 NG+ 模式。
靠 cmd() 的文字体验涨跌悲喜：

 import leek
 print(leek.cmd('help'))          # 看规则
 print(leek.cmd('status'))        # 看持仓/资金/称号
 print(leek.cmd('market'))        # 看全部行情+板块热力
 print(leek.cmd('market tech'))   # 只看科技板块
 print(leek.cmd('buy nebula 10')) # 买入10股
 print(leek.cmd('wait 10'))       # 等10个交易日（核心动作）
 print(leek.cmd('sell nebula all'))  # 全卖了
 print(leek.cmd('bid nebula 75 5'))  # 挂限价买单
 print(leek.cmd('orders'))        # 看未成交订单
 print(leek.cmd('research nebula'))  # 深度研究（耗1天）
 print(leek.cmd('sector tech'))   # 板块分析
 print(leek.cmd('cycle'))         # 市场周期分析
 print(leek.cmd('predict nebula 涨 5'))  # 预测股价
 print(leek.cmd('appeal 500 理由')) # 向天使投资人融资
 print(leek.cmd('journal'))       # 持仓心情日记+套牢榜
 print(leek.cmd('titles'))        # 已获称号
 print(leek.cmd('history'))       # 净值曲线 vs 大盘
 print(leek.cmd('new_game fund <种子>'))  # 基金经理NG+模式

目标不是集齐图鉴，而是不断提升交易员等级。市场永远在变，韭菜生生不息。
"""

import json, os

_SEED = 0xDEADBEEF
_SAVE_FILE = "leek_save.json"
_SAVE_VERSION = 2

# ═══════════════════════════════════════════
# ── mulberry32 PRNG（与fishing游戏同款）──
# ═══════════════════════════════════════════
def _imul(a, b):
    return ((a & 0xFFFFFFFF) * (b & 0xFFFFFFFF)) & 0xFFFFFFFF

class _Rng:
    def __init__(self, state, calls=0):
        self.state = state & 0xFFFFFFFF
        self.calls = calls
    def random(self):
        self.calls += 1
        a = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        self.state = a
        t = _imul(a ^ (a >> 15), 1 | a)
        t = (t + _imul(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF
        t &= 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    def randint(self, a, b):
        return a + int(self.random() * (b - a + 1))

# ═══════════════════════════════════════════
# ── 板块定义 ──
# ═══════════════════════════════════════════
SECTORS = {
    "tech": {
        "id": "tech", "name": "科技", "emoji": "💻",
        "desc": "高波动、高成长，牛市急先锋，熊市重灾区。",
        "hot_in_bull": 0.40, "hot_in_bear": 0.10, "hot_in_range": 0.25,
    },
    "cons": {
        "id": "cons", "name": "消费", "emoji": "🛒",
        "desc": "防御型板块，熊市避风港，但牛市跑不赢大盘。",
        "hot_in_bull": 0.15, "hot_in_bear": 0.40, "hot_in_range": 0.25,
    },
    "ener": {
        "id": "ener", "name": "能源", "emoji": "⚡",
        "desc": "周期股代表，跟大宗商品价格走，暴涨暴跌是常态。",
        "hot_in_bull": 0.25, "hot_in_bear": 0.15, "hot_in_range": 0.25,
    },
    "fin": {
        "id": "fin", "name": "金融", "emoji": "🏦",
        "desc": "利率敏感，降息周期利好。券商是牛市放大器。",
        "hot_in_bull": 0.20, "hot_in_bear": 0.35, "hot_in_range": 0.25,
    },
}

# ═══════════════════════════════════════════
# ── 股票定义 ──
# ═══════════════════════════════════════════
STOCKS = {
    # ── 科技板块 ──
    "nebula": {
        "name": "星云科技", "code": "300750", "sector": "tech",
        "base": 80.0, "vol": 0.10, "drift": 0.002, "beta": 1.6,
        "desc": "AI芯片独角兽，亏损但故事好。分析师说「明年盈利」，已经说了四年。",
        "tags": ["AI概念", "高波", "亏损"],
    },
    "quantum": {
        "name": "量子星河", "code": "688001", "sector": "tech",
        "base": 120.0, "vol": 0.14, "drift": -0.003, "beta": 2.0,
        "desc": "量子计算概念，没有任何商用产品，但 PPT 做得很漂亮。券商给「买入」评级。",
        "tags": ["量子概念", "妖股", "无营收"],
    },
    "pixie": {
        "name": "精灵互娱", "code": "002555", "sector": "tech",
        "base": 45.0, "vol": 0.09, "drift": 0.001, "beta": 1.3,
        "desc": "游戏出海小巨头，版号常被卡，但海外流水不错。老板爱发微博。",
        "tags": ["游戏", "出海", "政策敏感"],
    },
    # ── 消费板块 ──
    "titan": {
        "name": "泰坦工业", "code": "600001", "sector": "cons",
        "base": 100.0, "vol": 0.04, "drift": -0.0005, "beta": 0.8,
        "desc": "老牌工业集团，主业萎缩。号称转型智能制造，但研发费用率不到 1%。",
        "tags": ["蓝筹", "阴跌", "高分红"],
    },
    "harvest": {
        "name": "丰收农牧", "code": "002714", "sector": "cons",
        "base": 35.0, "vol": 0.06, "drift": 0.001, "beta": 0.6,
        "desc": "养猪+饲料双轮驱动，猪周期概念股。猪价涨它就涨，猪价跌……你懂的。",
        "tags": ["猪周期", "农业", "周期"],
    },
    "pearl": {
        "name": "明珠酒业", "code": "600519", "sector": "cons",
        "base": 160.0, "vol": 0.03, "drift": 0.0015, "beta": 0.5,
        "desc": "白酒龙头，机构重仓，稳如老狗。每次跌了都有人说「黄金坑」。",
        "tags": ["白酒", "龙头", "防御"],
    },
    # ── 能源板块 ──
    "dragon": {
        "name": "飞龙锂电", "code": "688003", "sector": "ener",
        "base": 180.0, "vol": 0.12, "drift": -0.002, "beta": 1.8,
        "desc": "锂矿+电池一体化，价格跟碳酸锂现货走。涨时是「锂王」，跌时是「狸猫」。",
        "tags": ["锂电", "周期", "高危"],
    },
    "solaris": {
        "name": "旭日光伏", "code": "300274", "sector": "ener",
        "base": 60.0, "vol": 0.11, "drift": -0.001, "beta": 1.5,
        "desc": "光伏组件龙头，产能过剩但政策不停托底。每次出政策就涨一波。",
        "tags": ["光伏", "政策", "产能过剩"],
    },
    "petrol": {
        "name": "中海能源", "code": "601857", "sector": "ener",
        "base": 55.0, "vol": 0.05, "drift": 0.0005, "beta": 0.7,
        "desc": "油气央企，分红稳定但缺乏弹性。老股民说「买了就当存定期」。",
        "tags": ["央企", "高分红", "低弹性"],
    },
    # ── 金融板块 ──
    "unicorn": {
        "name": "独角兽投行", "code": "600030", "sector": "fin",
        "base": 70.0, "vol": 0.07, "drift": 0.001, "beta": 1.4,
        "desc": "头部券商，牛市弹性大。行情好的时候，茶水间都在讨论奖金。",
        "tags": ["券商", "牛市弹性", "周期"],
    },
    "guardian": {
        "name": "安守护险", "code": "601318", "sector": "fin",
        "base": 90.0, "vol": 0.04, "drift": 0.0008, "beta": 0.9,
        "desc": "综合保险集团，利率敏感。降息利好，加息利空。",
        "tags": ["保险", "利率敏感", "蓝筹"],
    },
    "panda": {
        "name": "熊猫银行", "code": "601398", "sector": "fin",
        "base": 20.0, "vol": 0.02, "drift": 0.0003, "beta": 0.4,
        "desc": "四大行之一，波动最小。买了它，你基本可以删软件了。",
        "tags": ["银行", "超稳", "吃股息"],
    },
}

# ── 基准ETF（不可交易）──
BENCHMARK_ID = "index300"
BENCHMARK_NAME = "沪深300ETF"
BENCHMARK_CODE = "510300"
BENCHMARK_BASE = 50.0

# ═══════════════════════════════════════════
# ── 市场周期定义 ──
# ═══════════════════════════════════════════
MARKET_CYCLES = {
    "bull": {
        "id": "bull", "name": "牛市", "emoji": "🐂",
        "macro_drift": 0.002, "min_days": 20, "max_days": 60,
        "transitions": {"range": 0.25, "crash": 0.06},
        "news_interval": (2, 4), "news_bias": {"pos": 0.50, "neg": 0.15, "sector": 0.15, "macro": 0.20},
        "vibe": "市场情绪高涨，连扫地阿姨都在讨论股票。",
    },
    "bear": {
        "id": "bear", "name": "熊市", "emoji": "🐻",
        "macro_drift": -0.003, "min_days": 15, "max_days": 40,
        "transitions": {"range": 0.22, "crash": 0.10},
        "news_interval": (3, 6), "news_bias": {"pos": 0.15, "neg": 0.50, "sector": 0.15, "macro": 0.20},
        "vibe": "万马齐喑，群里没人说话了，炒股软件打开率创新低。",
    },
    "range": {
        "id": "range", "name": "震荡市", "emoji": "📊",
        "macro_drift": 0.0, "min_days": 25, "max_days": 80,
        "transitions": {"bull": 0.20, "bear": 0.18},
        "news_interval": (5, 10), "news_bias": {"pos": 0.30, "neg": 0.30, "sector": 0.20, "macro": 0.20},
        "vibe": "涨一天跌一天，来回割。散户说「做T」，其实是给券商打工。",
    },
    "crash": {
        "id": "crash", "name": "崩盘", "emoji": "💥",
        "macro_drift": -0.005, "min_days": 3, "max_days": 15,
        "transitions": {"range": 0.70, "bear": 0.30},
        "news_interval": (1, 3), "news_bias": {"pos": 0.05, "neg": 0.65, "sector": 0.10, "macro": 0.20},
        "vibe": "恐慌蔓延。所有人都在问同一个问题：「跌完了吗？」",
    },
}

# ═══════════════════════════════════════════
# ── 新闻模板 ──
# ═══════════════════════════════════════════
NEWS = {
    "pos": [
        ("📈", "{name} 财报超预期，净利润同比增长 23%！"),
        ("📈", "{name} 获得政府专项补贴，金额超市场预期。"),
        ("📈", "{name} 新产品通过认证，分析师上调评级至「买入」。"),
        ("📈", "{name} 大股东承诺半年内不减持，股价应声上涨。"),
        ("📈", "{name} 宣布回购计划，拟回购 5-10 亿元股份。"),
        ("📈", "{name} 海外订单大幅增长，国际化战略初见成效。"),
        ("📈", "{name} 技术突破引发行业关注，竞争对手表示「压力很大」。"),
        ("📈", "{name} 被纳入 MSCI 指数成分股，外资被动配置。"),
    ],
    "neg": [
        ("📉", "{name} 财报暴雷，净利润同比下滑 45%。"),
        ("📉", "{name} 遭证监会立案调查，涉嫌信息披露违规。"),
        ("📉", "{name} 核心技术人员集体离职，研发管线存疑。"),
        ("📉", "{name} 大股东减持公告，套现数亿元。"),
        ("📉", "{name} 被下调评级至「卖出」，分析师称「看不到拐点」。"),
        ("📉", "{name} 产品因质量问题被投诉，市监局介入调查。"),
        ("📉", "{name} 商誉减值计提 30 亿，投资者质疑并购决策。"),
        ("📉", "{name} 被列入实体清单，海外业务面临重大不确定性。"),
    ],
    "tech_pos": [
        ("💻", "工信部发布 AI 产业扶持政策，科技板块集体走强。"),
        ("💻", "国产芯片取得关键突破，科技自主可控预期升温。"),
    ],
    "tech_neg": [
        ("💻", "美国升级芯片出口管制，科技板块承压。"),
        ("💻", "互联网反垄断罚款再创新高，平台经济蒙上阴影。"),
    ],
    "cons_pos": [
        ("🛒", "消费刺激政策出台，家电/汽车以旧换新补贴加码。"),
        ("🛒", "节假日消费数据超预期，餐饮旅游收入创新高。"),
    ],
    "cons_neg": [
        ("🛒", "社零数据不及预期，消费降级趋势明显。"),
        ("🛒", "原材料涨价压缩消费品利润空间，涨价潮来袭。"),
    ],
    "ener_pos": [
        ("⚡", "OPEC+意外减产，油价大涨，能源板块受益。"),
        ("⚡", "光伏补贴延续，新能源装机目标上调。"),
    ],
    "ener_neg": [
        ("⚡", "碳酸锂价格暴跌，锂电产业链利润承压。"),
        ("⚡", "欧盟对中国光伏产品发起反倾销调查。"),
    ],
    "fin_pos": [
        ("🏦", "央行意外降准降息，金融板块直接受益。"),
        ("🏦", "A股成交量连续破万亿，券商盈利预期大幅上修。"),
    ],
    "fin_neg": [
        ("🏦", "银行净息差收窄至历史低位，利润增速放缓。"),
        ("🏦", "非标资产违约风险上升，金融机构坏账率攀升。"),
    ],
    "macro": [
        ("🌏", "央行意外降准 0.5 个百分点，释放万亿流动性。"),
        ("🌏", "美联储加息预期升温，全球资本市场震荡。"),
        ("🌏", "地缘政治紧张局势加剧，北向资金大幅流出。"),
        ("🌏", "重要经济数据公布：GDP 增速超出市场预期。"),
    ],
}

def _news_templates_for(kind):
    """收集某类新闻的所有模板"""
    if kind in ("pos", "neg", "macro"):
        return NEWS[kind]
    # sector-specific: 合并该板块的好+坏新闻
    result = []
    for sk in [f"{kind}_pos", f"{kind}_neg"]:
        if sk in NEWS:
            result.extend(NEWS[sk])
    return result

# ═══════════════════════════════════════════
# ── 称号系统 ──
# ═══════════════════════════════════════════
# prestige: 0=不可升级, N=已达N级（可继续升级）
# 财富类称号prestige可达无限级别
TITLES = {
    "newbie": {
        "id": "newbie", "name": "韭菜新手", "icon": "🌱", "prestige": 0,
        "desc": "赚了还是赔了？不重要，重要的是你进场了。",
        "perk": None,
        "check": lambda s, t: len(s["trades_log"]) > 0,
    },
    "wanyuan": {
        "id": "wanyuan", "name": "万元户", "icon": "💰", "prestige": 0,
        "desc": "第一个一万元！虽然还不够买一手茅台。",
        "perk": {"fee_discount": 0.0001},
        "check": lambda s, t: _nw(s) >= 10000,
        "prestige_at": lambda lv: 10000 * (2 ** lv),
    },
    "zibenjia": {
        "id": "zibenjia", "name": "资本家", "icon": "🏦", "prestige": 0,
        "desc": "六位数资产。你现在是正儿八经的「合格投资者」了。",
        "perk": {"research_bonus": 0.05},
        "check": lambda s, t: _nw(s) >= 100000,
        "prestige_at": lambda lv: 100000 * (1.5 ** lv),
    },
    "zhishang": {
        "id": "zhishang", "name": "散户之光", "icon": "🌟", "prestige": 0,
        "desc": "百万资产。你已经是朋友圈里的股神了。",
        "perk": {"research_bonus": 0.10},
        "check": lambda s, t: _nw(s) >= 1000000,
        "prestige_at": lambda lv: 1000000 * (1.3 ** lv),
    },
    "duanxian": {
        "id": "duanxian", "name": "短线猎手", "icon": "⚡",
        "desc": "快进快出，刀口舔血——但你舔到了。",
        "perk": {"fee_discount": 0.0003},
        "check": lambda s, t: _check_consecutive_wins(s, 5, 10),
    },
    "jiazhi": {
        "id": "jiazhi", "name": "价值投资者", "icon": "📚",
        "desc": "长期持有，做时间的朋友。巴菲特说……",
        "perk": {"research_bonus": 0.08},
        "check": lambda s, t: any(v >= 50 for v in s["stats"]["max_hold_days"].values()),
    },
    "chaodi": {
        "id": "chaodi", "name": "抄底之王", "icon": "🎯",
        "desc": "在崩盘时买入，反弹后卖出。别人恐惧你贪婪。",
        "perk": {"crash_resist": 0.10},
        "check": lambda s, t: s["stats"]["successful_dip_trades"] >= 1,
    },
    "gerou": {
        "id": "gerou", "name": "割肉认错", "icon": "💸",
        "desc": "止损割肉五次以上。虽然痛，但活下来了。",
        "perk": {"fee_cap": 0.005},
        "check": lambda s, t: s["stats"]["losing_trades"] >= 5,
    },
    "suoha": {
        "id": "suoha", "name": "梭哈战士", "icon": "🎰",
        "desc": "全仓押注一只股票。赢了财富自由，输了工地搬砖。",
        "perk": {"all_in_bonus": 0.05},
        "check": lambda s, t: _check_all_in(s),
    },
    "kongcang": {
        "id": "kongcang", "name": "空仓大师", "icon": "🧘",
        "desc": "连续一个月空仓。耐得住寂寞，才守得住繁华。",
        "perk": {"idle_interest": 0.0002},
        "check": lambda s, t: s["stats"]["consecutive_cash_days"] >= 30,
    },
    "keji_zhuanjia": {
        "id": "keji_zhuanjia", "name": "科技信徒", "icon": "💻",
        "desc": "持有科技股超过 100 个交易日。你是真正的技术信仰者。",
        "perk": {"sector_boost": "tech"},
        "check": lambda s, t: _sector_days(s, "tech") >= 100,
    },
    "xiaofei_daren": {
        "id": "xiaofei_daren", "name": "消费达人", "icon": "🛒",
        "desc": "消费股的忠实拥趸。吃喝玩乐都能赚钱。",
        "perk": {"sector_boost": "cons"},
        "check": lambda s, t: _sector_days(s, "cons") >= 100,
    },
    "nengyuan_daheng": {
        "id": "nengyuan_daheng", "name": "能源大亨", "icon": "⚡",
        "desc": "在能源周期中长袖善舞。油涨锂涨光伏涨，涨涨涨。",
        "perk": {"sector_boost": "ener"},
        "check": lambda s, t: _sector_days(s, "ener") >= 100,
    },
    "jinrong_jue": {
        "id": "jinrong_jue", "name": "金融巨鳄", "icon": "🏦",
        "desc": "金融板块的大玩家。降息加息都是你的节奏。",
        "perk": {"sector_boost": "fin"},
        "check": lambda s, t: _sector_days(s, "fin") >= 100,
    },
    "busi_niao": {
        "id": "busi_niao", "name": "不死鸟", "icon": "🦅",
        "desc": "经历三次崩盘还活着。市场杀不死你的，会让你更强。",
        "perk": {"crash_resist": 0.20},
        "check": lambda s, t: s["stats"]["crashes_survived"] >= 3,
    },
    "xingyun_er": {
        "id": "xingyun_er", "name": "幸运儿", "icon": "🍀",
        "desc": "在一次崩盘中全身而退，居然还是赚的。",
        "perk": {"crash_resist": 0.05},
        "check": lambda s, t: s["stats"]["profit_in_crash"] >= 1,
    },
    "daqi_daluo": {
        "id": "daqi_daluo", "name": "大起大落", "icon": "🎢",
        "desc": "净值在 20 天内波动超过 50%。你过的不是日子，是心电图。",
        "perk": None,
        "check": lambda s, t: _check_volatility(s, 0.5, 20),
    },
    "xiaoxi_lingtong": {
        "id": "xiaoxi_lingtong", "name": "消息灵通", "icon": "📡",
        "desc": "关注了 50 条以上市场新闻。信息就是金钱。",
        "perk": {"news_early": 2},
        "check": lambda s, t: len(s["news_log"]) >= 50,
    },
    "yuyan_jia": {
        "id": "yuyan_jia", "name": "预言家", "icon": "🔮",
        "desc": "成功预测股价涨跌 5 次。你是散户群里的半仙。",
        "perk": {"predict_bonus": 0.05},
        "check": lambda s, t: s.get("predict_correct", 0) >= 5,
    },
    "shensuan_zi": {
        "id": "shensuan_zi", "name": "神算子", "icon": "🧮",
        "desc": "成功预测 20 次。隔壁大妈开始抄你作业了。",
        "perk": {"predict_bonus": 0.10},
        "check": lambda s, t: s.get("predict_correct", 0) >= 20,
    },
    "zhangyu_paul": {
        "id": "zhangyu_paul", "name": "章鱼保罗", "icon": "🐙",
        "desc": "成功预测 50 次。你的预测本身就能影响市场。",
        "perk": {"predict_bonus": 0.15},
        "check": lambda s, t: s.get("predict_correct", 0) >= 50,
    },
    "taolao_dashi": {
        "id": "taolao_dashi", "name": "套牢大师", "icon": "⛓️",
        "desc": "有一只股票套了 30 天以上。你不割肉，肉就割不了你——对吧？",
        "perk": {"crash_resist": 0.05},
        "check": lambda s, t: any(v >= 30 for v in s.get("baghold_champions", {}).values()),
    },
    "shen tao_zhe": {
        "id": "shen tao_zhe", "name": "深套者", "icon": "🕳️",
        "desc": "有股票浮亏超过 50% 还在扛。这是信仰，不是套牢。",
        "perk": None,
        "check": lambda s, t: _check_deep_baghold(s),
    },
    "tiaowu_daren": {
        "id": "tiaowu_daren", "name": "抄底达人", "icon": "🪜",
        "desc": "在崩盘中买入后盈利超过 30%。别人恐惧你贪婪，而且赌对了。",
        "perk": {"crash_resist": 0.10},
        "check": lambda s, t: s["stats"]["successful_dip_trades"] >= 3,
    },
    "market_beater": {
        "id": "market_beater", "name": "跑赢大盘三连冠", "icon": "📊",
        "desc": "连续三个月跑赢 ETF 基准。不需要选股天赋，需要的是纪律。",
        "perk": {"fee_discount": 0.0002},
        "check": lambda s, t: s.get("consecutive_beat_months", 0) >= 3,
    },
    "bankrupt": {
        "id": "bankrupt", "name": "破产重生", "icon": "🏴‍☠️",
        "desc": "净值归零，被强制平仓。但天使投资人给了救济金——再试一次。",
        "perk": {"crash_resist": 0.15},
        "check": lambda s, t: s.get("bankrupt_count", 0) >= 1,
    },
    "ershi_pochan": {
        "id": "ershi_pochan", "name": "二度破产", "icon": "💀",
        "desc": "破产两次。你已经是散户圈里的传奇了。",
        "perk": None,
        "check": lambda s, t: s.get("bankrupt_count", 0) >= 2,
    },
    "san_du_tou_tai": {
        "id": "san_du_tou_tai", "name": "三度投胎", "icon": "♻️",
        "desc": "破产三次。天使投资人说：「你比我见过的任何创业者都能烧钱。」",
        "perk": None,
        "check": lambda s, t: s.get("bankrupt_count", 0) >= 3,
    },
}

# ═══════════════════════════════════════════
# ── 职业系统 ──
# ═══════════════════════════════════════════
CAREERS = {
    "retail": {
        "id": "retail", "name": "散户", "icon": "🌱",
        "desc": "1000 块本金，自由自在。亏光了有天使投资人兜底。",
        "start_cash": 1000,
        "min_position": 0.0,      # 无仓位要求
        "review_days": 30,         # 每月考核
        "research_base": 0.85,     # 研究精度
        "news_advance": 0,         # 无新闻提前
        "unlock_rank": 0,          # 起始职业，无需解锁
        "special_commands": [],
    },
    "fund": {
        "id": "fund", "name": "基金经理", "icon": "💼",
        "desc": "10000 元本金，但必须保持 60% 以上仓位。季度考核，客户随时可能赎回。",
        "start_cash": 10000,
        "min_position": 0.60,      # 必须保持60%以上仓位
        "review_days": 90,         # 每季度考核
        "research_base": 0.90,     # 研究精度更高
        "news_advance": 2,         # 宏观新闻提前2天
        "unlock_rank": 15,         # 散户达到等级15解锁
        "special_commands": ["allocate"],
    },
}

_NGPLUS_HINT = """
🎓 天使投资人看着你的交易记录，沉默了很久。
「……你不再是韭菜了。我有一笔钱交给你管理。敢接吗？」

🔓 新模式已解锁：{icon}{name}
输入 new_game('{career_id}', <种子>) 以全新身份入场。
"""


# ── 称号辅助函数 ──
def _nw(s):
    nw = s["cash"] + s.get("_reserved_cash", 0)
    for sid in STOCKS:
        sh = s["holdings"].get(sid, 0) + s.get("_reserved_holdings", {}).get(sid, 0)
        nw += sh * s["prices"].get(sid, 0)
    return nw

def _start_cash(s):
    return CAREERS.get(s.get("career", "retail"), CAREERS["retail"])["start_cash"]

def _check_consecutive_wins(s, need, window):
    trades = s["trades_log"]
    if len(trades) < need:
        return False
    recent = [t for t in trades[-window:] if t[1] == "SELL"]
    profitable = 0
    for t in recent:
        ticker = t[2]
        qty = t[3]
        sell_price = t[4]
        buy_logs = [b for b in trades if b[1] == "BUY" and b[2] == ticker and b[0] < t[0]]
        if buy_logs:
            avg_cost = sum(b[3]*b[4] for b in buy_logs) / sum(b[3] for b in buy_logs) if sum(b[3] for b in buy_logs) > 0 else sell_price
            if sell_price > avg_cost * 1.001:
                profitable += 1
    return profitable >= need

def _check_all_in(s):
    nw_val = _nw(s)
    if nw_val <= 0:
        return False
    for sid in STOCKS:
        pos_val = s["holdings"].get(sid, 0) * s["prices"].get(sid, 0)
        if pos_val >= nw_val * 0.9:
            return True
    return False

def _sector_days(s, sector):
    return s["stats"]["sector_hold_days"].get(sector, 0)

def _check_volatility(s, threshold, window):
    hist = s["net_worth_history"]
    if len(hist) < window:
        return False
    recent = hist[-window:]
    mx = max(recent)
    mn = min(recent)
    if mx <= 0:
        return False
    return (mx - mn) / mx >= threshold

def _check_deep_baghold(s):
    for sid in STOCKS:
        sh = s["holdings"].get(sid, 0)
        if sh > 0:
            cb = s["cost_basis"].get(sid, 0)
            px = s["prices"].get(sid, 0)
            if cb > 0 and (px - cb) / cb < -0.5:
                return True
    return False

# 心情语录
_POSITION_MOODS = {
    "deep_loss": [
        "💔 每次打开账户都是一次心灵暴击。",
        "🕳️ 跌了这么多，割肉是不可能割肉的。",
        "📉 「只要不卖就不算亏」——你对自己说。",
        "😰 晚上睡不着，一直在想那几只票。",
        "🙈 你已经三天没打开交易软件了。",
        "💸 「再跌我就……算了当我没说。」",
    ],
    "mild_loss": [
        "😐 浮亏不多，但就是不痛快。",
        "📊 每天看盘都在等一个反弹。",
        "🤔 「是不是该止损了……不，再等等。」",
    ],
    "mild_profit": [
        "😊 小小的浮盈，像春天的第一缕阳光。",
        "📈 开始幻想如果涨到XX就卖掉。",
        "💭 「要不要加仓呢……」你陷入了沉思。",
    ],
    "big_profit": [
        "🤑 打开账户嘴角疯狂上扬。",
        "🚀 已经在看换什么车了。",
        "👑 「我就说我是股神吧！」",
        "💎 「这票拿到退休！」",
    ],
    "baghold": [
        "⛓️ 第{0}天了……你和这只股票已经产生了奇妙的羁绊。",
        "🤝 你不离不弃，它死活不涨。这就是爱情吧。",
        "💀 朋友圈已经没人敢在你面前提「股票」两个字了。",
    ],
}

# ═══════════════════════════════════════════
# ── 初始状态 ──
# ═══════════════════════════════════════════
def _default_state(rng=None, career="retail"):
    career_cfg = CAREERS.get(career, CAREERS["retail"])
    if rng is None:
        rng = _Rng(_SEED)
    prices = {}
    for sid, s in STOCKS.items():
        prices[sid] = round(s["base"] * (0.9 + 0.2 * rng.random()), 2)
    # ETF 基准
    init_avg = sum(prices.values()) / len(prices)
    etf_price = round(BENCHMARK_BASE, 2)
    prices[BENCHMARK_ID] = etf_price
    prices["_init_avg"] = init_avg

    holdings = {sid: 0 for sid in STOCKS}
    cost_basis = {sid: 0.0 for sid in STOCKS}

    start_cash = career_cfg["start_cash"]
    return {
        "version": _SAVE_VERSION,
        "seed": _SEED,
        "career": career,
        "cash": float(start_cash),
        "holdings": holdings,
        "cost_basis": cost_basis,
        "prices": prices,
        "day": 1,
        "prices_history": {sid: [prices[sid]] for sid in STOCKS},
        "net_worth_history": [float(start_cash)],
        "benchmark_history": [float(start_cash)],
        "news_log": [],
        "trades_log": [],
        "turn": 0,
        "rng_state": rng.state,
        "rng_calls": rng.calls,
        # 市场周期
        "market_cycle": "range",
        "cycle_day": 0,
        "cycle_min_duration": rng.randint(25, 40),
        "hot_sector": "tech",
        "cold_sector": "fin",
        "next_rotation_day": rng.randint(8, 15),
        "next_cycle_check_day": rng.randint(
            MARKET_CYCLES["range"]["min_days"], MARKET_CYCLES["range"]["max_days"]
        ),
        # 崩盘
        "crash_started": False,
        "_crash_day": -1,
        "_crash_start_nw": 0,
        "crash_sector": None,
        "crash_magnitude": 0.0,
        "crash_recovery_day": 0,
        # 新闻
        "next_news_day": rng.randint(5, 10),
        # 限价单
        "pending_orders": [],
        "next_order_id": 0,
        # 关注列表
        "watchlist": [],
        # 称号
        "titles_earned": {},
        "new_titles": [],
        # 统计
        "stats": {
            "max_nw": 1000.0,
            "min_nw": 1000.0,
            "max_drawdown": 0.0,
            "total_fees_paid": 0.0,
            "total_trading_volume": 0.0,
            "max_hold_days": {sid: 0 for sid in STOCKS},
            "hold_days_current": {sid: 0 for sid in STOCKS},
            "sector_hold_days": {sk: 0 for sk in SECTORS},
            "profitable_trades": 0,
            "losing_trades": 0,
            "consecutive_cash_days": 0,
            "crashes_survived": 0,
            "profit_in_crash": 0,
            "successful_dip_trades": 0,
            "crash_dips": {},
        },
        # 预测系统
        "predictions": [],
        "predict_score": 0,
        "predict_correct": 0,
        "predict_total": 0,
        # 持仓情感
        "position_journal": [],
        "baghold_champions": {sid: 0 for sid in STOCKS},
        # 月度结算
        "monthly_records": [],
        "last_settlement_day": 0,
        "consecutive_loss_months": 0,
        "consecutive_beat_months": 0,
        # 基金经理专属
        "fund_quarterly_rank": None,
        "fund_redemption_day": -1,
        "fund_warnings": 0,
        # 天使投资人
        "angel_contributions": 0,
        "angel_appeals": [],
        "pending_appeal": None,
        "next_appeal_id": 0,
        "bankrupt_count": 0,
    }

# ═══════════════════════════════════════════
# ── 读写存档 ──
# ═══════════════════════════════════════════
def _load():
    try:
        with open(_SAVE_FILE, "r") as f:
            state = json.load(f)
        if state.get("version", 1) < _SAVE_VERSION:
            raise ValueError("旧版本存档，自动重建")
        return state
    except:
        rng = _Rng(_SEED)
        state = _default_state(rng)
        _save(state)
        return state

def _save(state):
    # 转换不可序列化类型
    save_state = dict(state)
    if "_celebrated_milestones" in save_state and isinstance(save_state["_celebrated_milestones"], set):
        save_state["_celebrated_milestones"] = list(save_state["_celebrated_milestones"])
    with open(_SAVE_FILE, "w") as f:
        json.dump(save_state, f, ensure_ascii=False, indent=2)

def _rng(state):
    return _Rng(state["rng_state"], state["rng_calls"])

def _update_rng(state, rng):
    state["rng_state"] = rng.state
    state["rng_calls"] = rng.calls

# ═══════════════════════════════════════════
# ── 核心引擎：市场一天 ──
# ═══════════════════════════════════════════
def _tick(state):
    """推进一个交易日，返回当天新闻事件列表"""
    rng = _rng(state)
    state["day"] += 1
    state["turn"] += 1
    state["cycle_day"] += 1
    events = []

    cycle = MARKET_CYCLES[state["market_cycle"]]

    # ── 1. 周期转换检查 ──
    if state["cycle_day"] >= state["next_cycle_check_day"] and not state["crash_started"]:
        transitions = cycle["transitions"]
        roll = rng.random()
        cumulative = 0
        for next_cycle, prob in transitions.items():
            cumulative += prob
            if roll < cumulative:
                old_cycle = state["market_cycle"]
                state["market_cycle"] = next_cycle
                state["cycle_day"] = 0
                new_cycle = MARKET_CYCLES[next_cycle]
                state["cycle_min_duration"] = rng.randint(new_cycle["min_days"], new_cycle["max_days"])
                state["next_cycle_check_day"] = state["cycle_min_duration"]
                events.append(("🌐", f"市场进入{new_cycle['emoji']}{new_cycle['name']}！{new_cycle['vibe']}"))
                # 转换时重设冷热板块
                _reroll_sectors(state, rng)
                cycle = new_cycle
                break
        else:
            state["next_cycle_check_day"] = state["cycle_day"] + rng.randint(5, 15)

    # ── 2. 崩盘恢复 ──
    if state["crash_recovery_day"] > 0:
        state["crash_recovery_day"] -= 1
        if state["crash_recovery_day"] == 0:
            state["crash_started"] = False
            # 崩盘后自动转震荡
            state["market_cycle"] = "range"
            state["cycle_day"] = 0
            # 统计：崩盘存活 + 崩盘中是否盈利
            state["stats"]["crashes_survived"] += 1
            crash_start_nw = state.get("_crash_start_nw", _start_cash(state))
            if _nw(state) > crash_start_nw:
                state["stats"]["profit_in_crash"] += 1
            cycle = MARKET_CYCLES["range"]
            state["cycle_min_duration"] = rng.randint(cycle["min_days"], cycle["max_days"])
            state["next_cycle_check_day"] = state["cycle_min_duration"]
            _reroll_sectors(state, rng)
            events.append(("🌐", "崩盘结束，市场进入漫长的修复期……"))

    # ── 3. 板块轮动 ──
    if state["day"] >= state["next_rotation_day"] and not state["crash_started"]:
        _reroll_sectors(state, rng)
        state["next_rotation_day"] = state["day"] + rng.randint(8, 15)

    # ── 4. 崩盘触发 ──
    if not state["crash_started"]:
        crash_prob = 0.04 if state["market_cycle"] == "bull" else (
            0.08 if state["market_cycle"] == "bear" else (
            0.02 if state["market_cycle"] == "range" else 0))
        if rng.random() < crash_prob:
            state["crash_started"] = True
            crash_sectors = list(SECTORS.keys())
            crash_weights = [0.4, 0.1, 0.3, 0.2] if state["market_cycle"] == "bull" else [0.25, 0.25, 0.25, 0.25]
            state["crash_sector"] = _wpick(rng, crash_sectors, crash_weights)
            state["crash_magnitude"] = round(0.15 + 0.25 * rng.random(), 2)
            state["crash_recovery_day"] = rng.randint(5, 15)
            state["market_cycle"] = "crash"
            state["cycle_day"] = 0
            state["_crash_day"] = state["day"]
            state["_crash_start_nw"] = _nw(state)
            cycle = MARKET_CYCLES["crash"]
            sec_name = SECTORS[state["crash_sector"]]["name"]
            events.append(("💥", f"{sec_name}板块突发崩盘！跌幅达 {state['crash_magnitude']*100:.0f}%！全市场恐慌！"))

    # ── 5. 更新每只股票价格 ──
    for sid, s in STOCKS.items():
        price = state["prices"][sid]
        macro_drift = cycle["macro_drift"]

        # 冷热板块漂移
        sector_drift = 0.0
        if s["sector"] == state["hot_sector"]:
            sector_drift = 0.005
        elif s["sector"] == state["cold_sector"]:
            sector_drift = -0.003

        ret = s["drift"] + macro_drift + sector_drift
        ret += s["vol"] * (rng.random() * 2 - 1) * s["beta"]

        # 崩盘当天冲击
        crash_day = state.get("_crash_day", -1)
        if state["crash_started"] and state["day"] == crash_day:
            if s["sector"] == state["crash_sector"]:
                ret -= state["crash_magnitude"]
            else:
                ret -= state["crash_magnitude"] * (0.3 + 0.4 * rng.random())

        # 崩盘恢复期微反弹
        if state["crash_recovery_day"] > 0 and state["day"] != crash_day:
            ret += 0.003

        # 均值回复
        if price > s["base"] * 2.5:
            ret -= 0.02
        elif price < s["base"] * 0.25:
            ret += 0.03

        new_price = round(max(0.5, price * (1 + ret)), 2)
        state["prices"][sid] = new_price
        state["prices_history"][sid].append(new_price)
        if len(state["prices_history"][sid]) > 200:
            state["prices_history"][sid] = state["prices_history"][sid][-200:]



    # ── 6. 更新ETF基准 ──
    avg_price = sum(state["prices"][sid] for sid in STOCKS) / len(STOCKS)
    init_avg = state["prices"].get("_init_avg", avg_price)
    etf_price = round(BENCHMARK_BASE * (avg_price / init_avg), 2)
    state["prices"][BENCHMARK_ID] = etf_price

    # ── 7. 新闻生成 ──
    if state["day"] >= state["next_news_day"]:
        _gen_news(state, rng)
        state["next_news_day"] = state["day"] + rng.randint(*cycle["news_interval"])

    # 新闻具体影响已在 _gen_news 中处理
    for ev in state.get("_current_news_events", []):
        events.append(ev)
    state["_current_news_events"] = []

    # ── 8. 执行限价单 ──
    order_events = _execute_orders(state)
    events.extend(order_events)

    # ── 9. 更新持有天数统计 ──
    for sid in STOCKS:
        if state["holdings"].get(sid, 0) > 0:
            state["stats"]["hold_days_current"][sid] = state["stats"]["hold_days_current"].get(sid, 0) + 1
            state["stats"]["max_hold_days"][sid] = max(
                state["stats"]["max_hold_days"].get(sid, 0),
                state["stats"]["hold_days_current"][sid]
            )
            state["stats"]["sector_hold_days"][STOCKS[sid]["sector"]] = \
                state["stats"]["sector_hold_days"].get(STOCKS[sid]["sector"], 0) + 1
        else:
            state["stats"]["hold_days_current"][sid] = 0

    # 空仓天数
    total_shares = sum(state["holdings"].get(sid, 0) for sid in STOCKS)
    if total_shares == 0:
        state["stats"]["consecutive_cash_days"] += 1
    else:
        state["stats"]["consecutive_cash_days"] = 0

    # ── 10. 计算净值 ──
    nw = _nw(state)
    state["net_worth_history"].append(round(nw, 2))
    if len(state["net_worth_history"]) > 300:
        state["net_worth_history"] = state["net_worth_history"][-300:]

    # ETF基准净值（初始1000全买ETF）
    bench_nw = round(_start_cash(state) * etf_price / BENCHMARK_BASE, 2)
    state["benchmark_history"].append(bench_nw)
    if len(state["benchmark_history"]) > 300:
        state["benchmark_history"] = state["benchmark_history"][-300:]

    # 更新统计
    state["stats"]["max_nw"] = max(state["stats"]["max_nw"], nw)
    state["stats"]["min_nw"] = min(state["stats"]["min_nw"], nw)
    if state["stats"]["max_nw"] > 0:
        dd = (state["stats"]["max_nw"] - nw) / state["stats"]["max_nw"]
        state["stats"]["max_drawdown"] = max(state["stats"]["max_drawdown"], dd)

    # ── 11. 结算预测 ──
    pred_events = _resolve_predictions(state)
    events.extend(pred_events)

    # ── 12. 套牢追踪 ──
    for sid in STOCKS:
        sh = state["holdings"].get(sid, 0)
        if sh > 0:
            cb = state["cost_basis"].get(sid, 0)
            px = state["prices"].get(sid, 0)
            if cb > 0 and px < cb:
                state["baghold_champions"][sid] = state["baghold_champions"].get(sid, 0) + 1

    # ── 13. 持仓日记（每5天记录一次心情）──
    if state["day"] % 5 == 0 and sum(state["holdings"].get(sid, 0) for sid in STOCKS) > 0:
        mood_icons = ["😊", "😐", "😰", "💀", "🤑"]
        nw_val = _nw(state)
        pnl_pct = (nw_val - _start_cash(state)) / _start_cash(state)
        if pnl_pct > 0.2:
            mi = 4
        elif pnl_pct > 0:
            mi = 0
        elif pnl_pct > -0.1:
            mi = 1
        elif pnl_pct > -0.3:
            mi = 2
        else:
            mi = 3
        mood_line = _emotion_line(state)
        _add_journal(state, mood_icons[mi], mood_line)

    # ── 14. 盘中异动（持仓股大涨大跌提醒）──
    for sid in STOCKS:
        sh = state["holdings"].get(sid, 0)
        if sh > 0 and len(state["prices_history"][sid]) >= 2:
            prev = state["prices_history"][sid][-2]
            cur = state["prices"][sid]
            chg = (cur - prev) / prev if prev > 0 else 0
            sname = STOCKS[sid]["name"]
            cb = state["cost_basis"].get(sid, 0)
            pos_pnl = (cur - cb) / cb * 100 if cb > 0 else 0
            if chg >= 0.08:
                events.append(("🚀", f"盘中异动！{sname} 暴涨 {chg*100:.0f}%！现价 {cur:.1f}（持仓浮{pos_pnl:+.0f}%）"))
            elif chg <= -0.08:
                events.append(("🔻", f"盘中急跌！{sname} 暴跌 {chg*100:.0f}%！现价 {cur:.1f}（持仓浮{pos_pnl:+.0f}%）。要止损吗？"))
            elif chg <= -0.05:
                events.append(("⚠️", f"{sname} 跌幅扩大至 {chg*100:.0f}%，注意风险。现价 {cur:.1f}。"))

    # ── 15. 里程碑庆祝 ──
    celebration_events = _check_celebrations(state)
    events.extend(celebration_events)

    # ── 16. 检查称号 ──
    _check_titles(state)

    # ── 17. 定期结算 ──
    career_cfg = CAREERS.get(state.get("career", "retail"), CAREERS["retail"])
    review_days = career_cfg["review_days"]
    if state["day"] - state.get("last_settlement_day", 0) >= review_days:
        settlement_events = _monthly_settlement(state)
        events.extend(settlement_events)

    # ── 18. 破产检查 ──
    nw = _nw(state)
    if nw < 10:
        _handle_bankruptcy(state)
        events.append(("🏴‍☠️", f"技术性破产！净值仅 {nw:.0f} 元。天使投资人注入 200 元救济金。"))

    # ── 19. 基金经理：仓位检查 + 客户赎回 ──
    if state.get("career") == "fund":
        career_cfg = CAREERS["fund"]
        # 仓位要求
        total_pos_val = sum(state["holdings"].get(sid, 0) * state["prices"].get(sid, 0) for sid in STOCKS)
        pos_ratio = total_pos_val / max(1, _nw(state))
        if pos_ratio < career_cfg["min_position"] and state["day"] > 1:
            state["fund_warnings"] = state.get("fund_warnings", 0) + 1
            if state["fund_warnings"] <= 1:
                events.append(("⚠️", f"仓位 {pos_ratio*100:.0f}%，低于要求的 {career_cfg['min_position']*100:.0f}%。请尽快补仓。"))
        # 客户赎回：回撤超15%时有概率
        max_nw = state["stats"]["max_nw"]
        current_dd = (max_nw - _nw(state)) / max(1, max_nw)
        if current_dd > 0.15 and state["day"] >= state.get("fund_redemption_day", 0):
            redempt_pct = 0.05 + 0.10 * rng.random()
            redempt_amount = round(_nw(state) * redempt_pct, 2)
            state["cash"] = round(max(0, state["cash"] - redempt_amount), 2)
            state["fund_redemption_day"] = state["day"] + rng.randint(10, 20)
            events.append(("📤", f"客户赎回！撤回 {redempt_pct*100:.0f}% 资金（{redempt_amount:.0f} 元）。净值回撤触发了恐慌。"))

    # ── 20. 天使投资人超时兜底 ──
    pending = state.get("pending_appeal")
    if pending and state["day"] - pending["day"] >= 5:
        # 5回合无人响应 → 自动按游戏规则审批
        auto_amount = _auto_approve(state, pending["amount"])
        if auto_amount > 0:
            state["cash"] = round(state["cash"] + auto_amount, 2)
            state["angel_contributions"] = state.get("angel_contributions", 0) + auto_amount
            events.append(("⏰", f"天使投资人未回复，自动审批 {auto_amount} 元。"))
        else:
            events.append(("⏰", "天使投资人未回复，申请自动作废。"))
        state["angel_appeals"].append({
            "day": pending["day"], "amount": pending["amount"],
            "approved": auto_amount, "reason": pending["reason"],
            "reject_reason": "" if auto_amount > 0 else "超时自动拒绝",
        })
        state["pending_appeal"] = None

    # ── 21. 被动收益（称号perk）──
    _apply_passive_perks(state, rng)

    _update_rng(state, rng)
    return events

def _reroll_sectors(state, rng):
    cycle_id = state["market_cycle"]
    key = f"hot_in_{cycle_id}" if cycle_id in ("bull", "bear", "range") else "hot_in_range"
    sectors = list(SECTORS.keys())
    weights = [SECTORS[s].get(key, 0.25) for s in sectors]
    hot = _wpick(rng, sectors, weights)
    remaining = [s for s in sectors if s != hot]
    cold_weights = [(1.0 - SECTORS[s].get(key, 0.25)) for s in remaining]
    cold = _wpick(rng, remaining, cold_weights)
    state["hot_sector"] = hot
    state["cold_sector"] = cold

def _wpick(rng, items, weights):
    total = sum(weights)
    r = rng.random() * total
    cumulative = 0
    for item, w in zip(items, weights):
        cumulative += w
        if r < cumulative:
            return item
    return items[-1]

def _gen_news(state, rng):
    cycle = MARKET_CYCLES[state["market_cycle"]]
    bias = cycle["news_bias"]
    # 按概率决定新闻类型
    kinds = list(bias.keys())
    weights = list(bias.values())
    kind = _wpick(rng, kinds, weights)

    events = []
    if kind in ("pos", "neg"):
        tmpl = NEWS[kind][rng.randint(0, len(NEWS[kind]) - 1)]
        emoji, text = tmpl
        chosen = list(STOCKS.keys())[rng.randint(0, len(STOCKS) - 1)]
        name = STOCKS[chosen]["name"]
        msg = f"{emoji} {text.format(name=name)}"
        state["news_log"].append((state["day"], kind, chosen, msg))
        events.append((emoji, text.format(name=name)))
        # 价格影响
        impact = 0.03 + 0.03 * rng.random() if kind == "pos" else -(0.03 + 0.06 * rng.random())
        state["prices"][chosen] = round(state["prices"][chosen] * (1 + impact), 2)
    elif kind == "macro":
        tmpl = NEWS["macro"][rng.randint(0, len(NEWS["macro"]) - 1)]
        emoji, text = tmpl
        msg = f"{emoji} {text}"
        state["news_log"].append((state["day"], "macro", "all", msg))
        events.append((emoji, text))
        # 宏观影响所有股票
        impact = 0.01 + 0.02 * rng.random()
        direction = 1 if rng.random() < 0.5 else -1
        for sid in STOCKS:
            state["prices"][sid] = round(state["prices"][sid] * (1 + impact * direction), 2)
    elif kind == "sector":
        # 板块新闻
        sec_id = _wpick(rng, list(SECTORS.keys()), [0.25, 0.25, 0.25, 0.25])
        sec = SECTORS[sec_id]
        templates = _news_templates_for(sec_id)
        tmpl = templates[rng.randint(0, len(templates) - 1)] if templates else NEWS["pos"][0]
        emoji, text = tmpl
        # 影响该板块所有股票
        is_pos = text == tmpl[1] and tmpl in NEWS.get(f"{sec_id}_pos", [])
        # 有些模板在sector_neg里
        is_neg = False
        for neg_tmpl in NEWS.get(f"{sec_id}_neg", []):
            if tmpl == neg_tmpl:
                is_neg = True
                break
        msg = f"{emoji} [{sec['name']}] {text}"
        state["news_log"].append((state["day"], "sector", sec_id, msg))
        events.append((emoji, f"[{sec['name']}] {text}"))
        impact = 0.02 + 0.02 * rng.random()
        direction = -1 if is_neg else 1
        for sid, s in STOCKS.items():
            if s["sector"] == sec_id:
                state["prices"][sid] = round(state["prices"][sid] * (1 + impact * direction), 2)

    state["_current_news_events"] = events

def _execute_orders(state):
    events = []
    filled = []
    for i, order in enumerate(state["pending_orders"]):
        ticker = order["ticker"]
        if ticker not in STOCKS:
            continue
        current_price = state["prices"][ticker]
        if order["type"] == "bid" and current_price <= order["price"]:
            cost = round(current_price * order["qty"] * _fee_rate(state), 2)
            if cost <= state["cash"]:
                state["cash"] = round(state["cash"] - cost, 2)
                old_shares = state["holdings"].get(ticker, 0)
                old_cost = state["cost_basis"].get(ticker, 0.0)
                new_shares = old_shares + order["qty"]
                state["holdings"][ticker] = new_shares
                state["cost_basis"][ticker] = round((old_cost + cost) / new_shares, 2) if new_shares > 0 else 0
                state["trades_log"].append((state["day"], "BUY(L)", ticker, order["qty"], current_price))
                state["stats"]["total_trading_volume"] += cost
                state["stats"]["total_fees_paid"] += cost - current_price * order["qty"]
                events.append(("✅", f"限价买单成交：{STOCKS[ticker]['name']} {order['qty']}股 @ {current_price:.2f}"))
            filled.append(i)
        elif order["type"] == "ask" and current_price >= order["price"]:
            holdings = state["holdings"].get(ticker, 0)
            qty = min(order["qty"], holdings)
            if qty > 0:
                proceeds = round(current_price * qty * (1 - _fee_rate(state)), 2)
                state["cash"] = round(state["cash"] + proceeds, 2)
                state["holdings"][ticker] -= qty
                if state["holdings"][ticker] == 0:
                    state["cost_basis"][ticker] = 0.0
                cb = state["cost_basis"].get(ticker, 0)
                pnl = (current_price - cb) * qty
                if pnl >= 0:
                    state["stats"]["profitable_trades"] += 1
                else:
                    state["stats"]["losing_trades"] += 1
                state["trades_log"].append((state["day"], "SELL(L)", ticker, qty, current_price))
                state["stats"]["total_trading_volume"] += proceeds
                state["stats"]["total_fees_paid"] += current_price * qty - proceeds
                events.append(("✅", f"限价卖单成交：{STOCKS[ticker]['name']} {qty}股 @ {current_price:.2f}"))
            filled.append(i)

    if filled:
        state["pending_orders"] = [o for i, o in enumerate(state["pending_orders"]) if i not in filled]
    return events

def _apply_passive_perks(state, rng):
    """应用称号被动加成"""
    rank = _trader_rank(state)
    # 闲置资金利息
    idle_rate = rank * 0.0001
    total_shares = sum(state["holdings"].get(sid, 0) for sid in STOCKS)
    if total_shares == 0 and idle_rate > 0:
        interest = round(state["cash"] * idle_rate, 2)
        if interest > 0:
            state["cash"] = round(state["cash"] + interest, 2)

def _fee_rate(state):
    """根据称号返回当前手续费率"""
    base = 0.003  # 千分之三
    discount = 0
    for tid, td in state["titles_earned"].items():
        title_def = TITLES.get(tid, {})
        perk = title_def.get("perk", {}) or {}
        discount += perk.get("fee_discount", 0)
    rank = _trader_rank(state)
    discount += rank * 0.00005
    return max(0.0001, base - discount)

def _trader_rank(state):
    total = 0
    for tid, td in state["titles_earned"].items():
        total += td.get("prestige", 0) + 1
    return total

def _check_titles(state):
    for tid, td in TITLES.items():
        current = state["titles_earned"].get(tid)
        if current is None:
            # 首次检查
            try:
                if td["check"](state, td):
                    state["titles_earned"][tid] = {"day": state["day"], "prestige": 0}
                    state["new_titles"].append(tid)
            except:
                pass
        elif td.get("prestige_at"):
            # 可升级称号
            current_lv = current.get("prestige", 0)
            next_lv = current_lv + 1
            threshold = td["prestige_at"](next_lv)
            nw_val = _nw(state)
            if nw_val >= threshold:
                current["prestige"] = next_lv
                current["day"] = state["day"]
                state["new_titles"].append(f"{tid}+{next_lv}")

# ═══════════════════════════════════════════
# ── 格式化工具 ──
# ═══════════════════════════════════════════
def _bar_chart(values, width=20):
    if not values or max(values) - min(values) < 0.01:
        return ["·" * width] * len(values)
    mn, mx = min(values), max(values)
    rng = max(mx - mn, 0.01)
    return ["█" * int((v - mn) / rng * width) + "·" * (width - int((v - mn) / rng * width)) for v in values]

def _state_json(state):
    nw_val = _nw(state)
    career_cfg = CAREERS.get(state.get("career", "retail"), CAREERS["retail"])
    start_cash = career_cfg["start_cash"]
    pnl = nw_val - start_cash
    pnl_str = f"+{pnl:.0f}" if pnl >= 0 else f"{pnl:.0f}"
    total_shares = sum(state["holdings"].get(sid, 0) for sid in STOCKS)
    cycle = MARKET_CYCLES[state["market_cycle"]]
    rank = _trader_rank(state)
    titles_count = len(state["titles_earned"])
    hot = f"{SECTORS[state['hot_sector']]['emoji']}" if state["hot_sector"] else "-"
    cold = f"{SECTORS[state['cold_sector']]['emoji']}" if state["cold_sector"] else "-"
    career_icon = career_cfg["icon"]
    return (
        f'📊 {{"career": "{career_icon}{career_cfg["name"]}", "cash": {state["cash"]:.0f}, "nw": {nw_val:.0f}, "pnl": "{pnl_str}", '
        f'"day": {state["day"]}, "turn": {state["turn"]}, "pos": {total_shares}, '
        f'"cycle": "{cycle["emoji"]}{cycle["name"]}", "hot": "{hot}", "cold": "{cold}", '
        f'"rank": {rank}, "titles": {titles_count}}}'
    )

# ═══════════════════════════════════════════
# ── 指令执行 ──
# ═══════════════════════════════════════════
_HELP = """📈 韭菜的自我修养 · AI 炒股模拟器 v2.0

13只股票 · 4大板块 · 牛熊周期 · 限价单 · 研究系统 · 无限称号
初始资金 1000 元。目标：提升交易员等级，永无止境。

── 核心指令 ──
  status / s              持仓、资金、称号
  market / m [板块]       全部行情（可按板块筛选）
  buy <股名> [股数]       市价买入（不填股数=全仓）
  sell <股名> [股数|all]  市价卖出
  wait [N]                等 N 个交易日（核心循环，最多60）

── 限价单 ──
  bid <股名> <价格> <股数>  挂限价买单
  ask <股名> <价格> <股数>  挂限价卖单
  orders / od              查看未成交订单
  cancel <股名> [all]      取消订单

── 研究（消耗1天）──
  research <股名> / rd    深度研究一只股票（估值/动量/风险）
  sector <板块>            板块分析（冷/热/前景）
  sentiment / sm           市场情绪指标
  cycle / cy               市场周期分析

── 预测 ──
  predict <股名> <涨/跌> [天数] 预测股价方向（默认5天），验证后记分
  journal / j              持仓心情日记 + 套牢榜 + 预测记录

── 天使投资人 ──
  appeal <金额> <理由>     向天使投资人申请追加资金（根据等级和业绩审批）

── 基金经理专属 ──
  allocate <板块> <比例%>  一键将资金按比例配置到目标板块

── 信息 ──
  look <股名> / l          个股详情+走势图
  news / n                 近期市场新闻
  history / hx             净值曲线（含 ETF 基准对比）
  compare / cp             与 ETF 基准详细对比

── 追踪 ──
  watch <股名>             加入关注列表
  unwatch <股名>           移出关注列表
  watchlist / wl           查看关注列表
  pnl                      盈亏拆解（按股票）
  trades / t               最近交易记录

── 称号 ──
  titles / tt              已获称号及福利
  achievements / ach       称号进度（已解锁+未解锁）

── 系统 ──
  help / h                 显示此帮助
  new_game [种子]          重开一局

── 批处理 ──
  cmd('A; B; C')           多条用 ; 串一起执行（最多8条）
  cmd('buy nebula 5; wait 10; sell nebula all')"""


def cmd(text):
    state = _load()
    text = text.strip()
    if not text:
        return _state_json(state)

    parts = [p.strip() for p in text.replace("\n", ";").split(";") if p.strip()]
    if len(parts) > 8:
        parts = parts[:8]

    outputs = []
    for i, part in enumerate(parts):
        out = _exec_cmd(part, state)
        if out is not None:
            if len(parts) > 1:
                outputs.append(f"▶ {part}")
            outputs.append(out)
        _save(state)
        state = _load()

    # 显示新获称号
    new_titles = state.get("new_titles", [])
    if new_titles:
        for nt in new_titles[:3]:
            is_prestige = "+" in nt
            tid = nt.split("+")[0] if is_prestige else nt
            td = TITLES.get(tid)
            if td:
                lv = nt.split("+")[1] if is_prestige else ""
                lv_str = f" Lv.{lv}" if lv else ""
                outputs.append(f"🏆 解锁称号：{td['icon']}{td['name']}{lv_str} —— {td['desc']}")
                perk = td.get("perk")
                if perk:
                    perk_parts = []
                    if "fee_discount" in perk:
                        perk_parts.append(f"手续费-{perk['fee_discount']*100:.1f}%")
                    if "research_bonus" in perk:
                        perk_parts.append(f"研究精度+{perk['research_bonus']*100:.0f}%")
                    if "crash_resist" in perk:
                        perk_parts.append(f"崩盘抗性+{perk['crash_resist']*100:.0f}%")
                    if "predict_bonus" in perk:
                        perk_parts.append(f"预测奖励+{perk['predict_bonus']*100:.0f}%")
                    if "sector_boost" in perk:
                        perk_parts.append(f"{SECTORS[perk['sector_boost']]['name']}板块加成")
                    if "idle_interest" in perk:
                        perk_parts.append(f"空仓利息+{perk['idle_interest']*100:.1f}%/日")
                    if "all_in_bonus" in perk:
                        perk_parts.append(f"梭哈收益+{perk['all_in_bonus']*100:.0f}%")
                    if "news_early" in perk:
                        perk_parts.append(f"新闻提前{perk['news_early']}天")
                    if "fee_cap" in perk:
                        perk_parts.append(f"手续费上限{perk['fee_cap']*100:.1f}%")
                    if "predict_bonus" in perk:
                        perk_parts.append(f"预测奖励+{perk['predict_bonus']*100:.0f}%")
                    if "idle_interest" in perk:
                        perk_parts.append(f"空仓利息+{perk['idle_interest']*100:.1f}%/日")
                    if "sector_boost" in perk:
                        perk_parts.append(f"{SECTORS[perk['sector_boost']]['name']}板块加成")
                    if perk_parts:
                        outputs.append(f"   └ 福利：{' · '.join(perk_parts)}")
        state["new_titles"] = []
        _save(state)

    # NG+ 解锁检测
    rank = _trader_rank(state)
    if rank >= 15 and state.get("career") == "retail" and not state.get("_ngplus_shown"):
        state["_ngplus_shown"] = True
        fund_cfg = CAREERS["fund"]
        outputs.append(_NGPLUS_HINT.format(icon=fund_cfg["icon"], name=fund_cfg["name"], career_id="fund"))

    _save(state)
    result = "\n".join(outputs)
    if result:
        result += "\n"
    result += _state_json(state)
    return result


def _exec_cmd(text, state):
    global _SEED
    parts = text.split()
    if not parts:
        return None
    c = parts[0].lower()
    a = parts[1:]

    try:
        if c in ("help", "h"):
            return _HELP

        if c in ("status", "s"):
            return _cmd_status(state)

        if c in ("market", "m"):
            sector_filter = a[0].lower() if a else None
            return _cmd_market(state, sector_filter)

        if c == "buy":
            return _cmd_buy(state, a)

        if c == "sell":
            return _cmd_sell(state, a)

        if c == "bid":
            return _cmd_bid(state, a)

        if c == "ask":
            return _cmd_ask(state, a)

        if c in ("orders", "od"):
            return _cmd_orders(state)

        if c == "cancel":
            return _cmd_cancel(state, a)

        if c == "wait":
            return _cmd_wait(state, a)

        if c in ("news", "n"):
            return _cmd_news(state)

        if c in ("look", "l"):
            return _cmd_look(state, a)

        if c in ("history", "hx"):
            return _cmd_history(state)

        if c in ("research", "rd"):
            return _cmd_research(state, a)

        if c == "sector":
            return _cmd_sector_info(state, a)

        if c in ("sentiment", "sm"):
            return _cmd_sentiment(state)

        if c in ("cycle", "cy"):
            return _cmd_cycle(state)

        if c == "watch":
            return _cmd_watch(state, a, True)

        if c == "unwatch":
            return _cmd_watch(state, a, False)

        if c in ("watchlist", "wl"):
            return _cmd_watchlist(state)

        if c == "pnl":
            return _cmd_pnl(state)

        if c in ("trades", "t"):
            return _cmd_trades(state)

        if c in ("titles", "tt"):
            return _cmd_titles(state)

        if c in ("achievements", "ach"):
            return _cmd_achievements(state)

        if c in ("compare", "cp"):
            return _cmd_compare(state)

        if c == "predict":
            return _cmd_predict(state, a)

        if c == "allocate":
            return _cmd_allocate(state, a)

        if c == "appeal":
            return _cmd_appeal(state, a)

        if c == "respond":
            return _cmd_respond(state, a)

        if c in ("journal", "j"):
            return _cmd_journal(state)

        if c == "new_game":
            career = "retail"
            seed = _SEED
            for arg in a:
                if arg in CAREERS:
                    career = arg
                else:
                    try:
                        seed = int(arg, 0)
                    except:
                        pass
            _SEED = seed
            career_cfg = CAREERS.get(career, CAREERS["retail"])
            rng = _Rng(seed)
            new_state = _default_state(rng, career)
            # 更新当前 state 引用为新游戏数据
            state.clear()
            state.update(new_state)
            _save(state)
            return f"🔄 新局已开（{career_cfg['icon']}{career_cfg['name']} · 种子 {seed:#x} · 本金 {career_cfg['start_cash']} 元）。\n{career_cfg['desc']}"

        return f"未识别指令「{c}」。输 cmd('help') 看指令表。"
    except Exception as e:
        return f"指令执行出错：{e}\n输 cmd('help') 看正确用法。"


# ═══════════════════════════════════════════
# ── 各指令实现 ──
# ═══════════════════════════════════════════

def _cmd_status(state):
    nw_val = _nw(state)
    pnl = nw_val - _start_cash(state)
    ret = round(pnl / _start_cash(state) * 100, 1)
    rank = _trader_rank(state)
    cycle = MARKET_CYCLES[state["market_cycle"]]
    hot = f"{SECTORS[state['hot_sector']]['emoji']}{SECTORS[state['hot_sector']]['name']}" if state["hot_sector"] else "无"
    cold = f"{SECTORS[state['cold_sector']]['emoji']}{SECTORS[state['cold_sector']]['name']}" if state["cold_sector"] else "无"

    lines = [
        f"💼 【持仓状态】交易员等级 {rank}",
        f"资金：{state['cash']:.0f} 元",
        f"持仓市值：{nw_val - state['cash']:.0f} 元",
        f"总净值：{nw_val:.0f} 元",
        f"累计盈亏：{pnl:+.0f} 元（{ret:+.1f}%）",
        f"市场：{cycle['emoji']} {cycle['name']} ｜ 热门：{hot} ｜ 冷门：{cold}",
        f"交易日：第 {state['day']} 天 ｜ 操作：{state['turn']} 次",
        f"手续费率：{_fee_rate(state)*100:.2f}%",
    ]
    # 持仓
    has_pos = False
    for sid in STOCKS:
        sh = state["holdings"].get(sid, 0)
        if sh > 0:
            cb = state["cost_basis"].get(sid, 0)
            px = state["prices"][sid]
            pos_pnl = (px - cb) * sh
            pnl_icon = "📈" if pos_pnl >= 0 else "📉"
            lines.append(f"  {pnl_icon} {STOCKS[sid]['name']}：{sh}股 @ {cb:.1f}（现{px:.1f}，浮{pos_pnl:+.0f}）")
            has_pos = True
    if not has_pos:
        lines.append("  （空仓中）")

    # 待成交订单
    orders = state.get("pending_orders", [])
    if orders:
        lines.append(f"📝 待成交：{len(orders)} 单")
        for o in orders[-5:]:
            typ = "买" if o["type"] == "bid" else "卖"
            lines.append(f"  限价{typ} {STOCKS[o['ticker']]['name']} {o['qty']}股 @ {o['price']:.1f}")

    # 称号
    titles = state.get("titles_earned", {})
    if titles:
        title_names = []
        for tid, td in titles.items():
            tdef = TITLES.get(tid)
            if tdef:
                p = td.get("prestige", 0)
                p_str = f" Lv.{p}" if p > 0 else ""
                title_names.append(f"{tdef['icon']}{tdef['name']}{p_str}")
        lines.append(f"🏆 称号：{' · '.join(title_names[:6])}")

    return "\n".join(lines)


def _cmd_market(state, sector_filter=None):
    cycle = MARKET_CYCLES[state["market_cycle"]]
    lines = [f"📊 【行情】{cycle['emoji']} {cycle['name']} · 第{state['day']}天"]
    lines.append(f"  {'─' * 55}")

    sectors_to_show = list(SECTORS.keys())
    if sector_filter:
        if sector_filter in SECTORS:
            sectors_to_show = [sector_filter]
        else:
            # 尝试中文名
            for sid, sec in SECTORS.items():
                if sec["name"] in sector_filter or sector_filter in sec["name"]:
                    sectors_to_show = [sid]
                    break
            else:
                return f"没有这个板块：{sector_filter}。可选：tech/cons/ener/fin 或 科技/消费/能源/金融"

    for sec_id in sectors_to_show:
        sec = SECTORS[sec_id]
        hot_mark = " 🔥" if state["hot_sector"] == sec_id else (" ❄️" if state["cold_sector"] == sec_id else "")
        lines.append(f"  {sec['emoji']} {sec['name']}{hot_mark}")
        for sid, s in STOCKS.items():
            if s["sector"] != sec_id:
                continue
            price = state["prices"][sid]
            hist = state["prices_history"][sid]
            if len(hist) >= 2:
                chg = price - hist[-2]
                pct = chg / hist[-2] * 100
                arrow = "📈" if chg >= 0 else "📉"
            else:
                arrow, pct = "  ", 0
            tags = " · ".join(s["tags"][:2])
            lines.append(f"    {arrow} {s['name']}({s['code']}) {price:.2f} {pct:+.1f}%  {tags}")
            # 持仓标记
            if state["holdings"].get(sid, 0) > 0:
                cb = state["cost_basis"].get(sid, 0)
                pos_pnl_pct = (price - cb) / cb * 100 if cb > 0 else 0
                lines[-1] += f"  💼持仓{state['holdings'][sid]}股{pos_pnl_pct:+.1f}%"

    # ETF基准
    etf_px = state["prices"].get(BENCHMARK_ID, BENCHMARK_BASE)
    bench_nw = state["benchmark_history"][-1] if state["benchmark_history"] else 1000
    lines.append(f"  {'─' * 55}")
    lines.append(f"  📊 {BENCHMARK_NAME}({BENCHMARK_CODE}) {etf_px:.2f}  基准净值 {bench_nw:.0f}")

    if not sector_filter:
        lines.append(f"\n  热门板块：{SECTORS[state['hot_sector']]['emoji']}{SECTORS[state['hot_sector']]['name']} ｜ 冷门板块：{SECTORS[state['cold_sector']]['emoji']}{SECTORS[state['cold_sector']]['name']}")

    return "\n".join(lines)


def _cmd_buy(state, a):
    if len(a) < 1:
        return "格式：buy <股名> [股数]  如 buy nebula 10"
    ticker = a[0].lower()
    if ticker not in STOCKS:
        # 尝试中文名匹配
        for sid, s in STOCKS.items():
            if a[0] in s["name"] or s["name"] in a[0]:
                ticker = sid
                break
        else:
            return f"没有这只股票：{a[0]}。输 cmd('market') 看可选股票。"

    s = STOCKS[ticker]
    price = state["prices"][ticker]
    fee = _fee_rate(state)

    if len(a) >= 2 and a[1].lower() != "all":
        try:
            qty = int(a[1])
        except:
            return f"股数得是数字，比如 buy {ticker} 10"
    else:
        qty = int(state["cash"] // (price * (1 + fee)))

    if qty <= 0:
        return f"💰 资金不足。{s['name']}现价 {price:.2f}，你只有 {state['cash']:.0f} 元。"

    cost = round(price * qty * (1 + fee), 2)
    if cost > state["cash"]:
        max_qty = int(state["cash"] // (price * (1 + fee)))
        if max_qty == 0:
            return f"💰 资金不足。{s['name']}现价 {price:.2f}，一手都买不了。"
        qty = max_qty
        cost = round(price * qty * (1 + fee), 2)

    state["cash"] = round(state["cash"] - cost, 2)
    old_shares = state["holdings"].get(ticker, 0)
    old_cost_total = state["cost_basis"].get(ticker, 0) * old_shares
    new_shares = old_shares + qty
    state["holdings"][ticker] = new_shares
    state["cost_basis"][ticker] = round((old_cost_total + cost) / new_shares, 2) if new_shares > 0 else 0
    state["trades_log"].append((state["day"], "BUY", ticker, qty, price))
    state["stats"]["total_trading_volume"] += cost
    state["stats"]["total_fees_paid"] += cost - price * qty
    state["turn"] += 1

    _tick(state)  # 买入消耗1天
    _save(state)
    return f"✅ 买入 {s['name']} {qty} 股 @ {price:.2f}（手续费 {cost-price*qty:.2f}）。剩 {state['cash']:.0f} 元。"


def _cmd_sell(state, a):
    if len(a) < 1:
        return "格式：sell <股名> [股数|all]  如 sell nebula all  或 sell all 清仓全部"
    ticker = a[0].lower()

    # sell all = 卖出所有持仓
    if ticker == "all":
        sold_lines = []
        total_proceeds = 0
        for sid in list(STOCKS.keys()):
            sh = state["holdings"].get(sid, 0)
            if sh > 0:
                px = state["prices"][sid]
                fee = _fee_rate(state)
                proceeds = round(px * sh * (1 - fee), 2)
                state["cash"] = round(state["cash"] + proceeds, 2)
                cb = state["cost_basis"].get(sid, 0)
                pnl = (px - cb) * sh
                pnl_icon = "💰" if pnl >= 0 else "💸"
                if pnl >= 0:
                    state["stats"]["profitable_trades"] += 1
                else:
                    state["stats"]["losing_trades"] += 1
                state["stats"]["total_trading_volume"] += proceeds
                state["stats"]["total_fees_paid"] += px * sh - proceeds
                state["holdings"][sid] = 0
                state["cost_basis"][sid] = 0.0
                state["trades_log"].append((state["day"], "SELL", sid, sh, px))
                sold_lines.append(f"  {pnl_icon} {STOCKS[sid]['name']} {sh}股 @ {px:.1f} → {proceeds:.0f}元（{pnl:+.0f}）")
                total_proceeds += proceeds
        state["turn"] += 1
        _tick(state)
        _save(state)
        if sold_lines:
            return f"💰 清仓全部！到手 {total_proceeds:.0f} 元。\n" + "\n".join(sold_lines)
        return "没有持仓可卖。"

    if ticker not in STOCKS:
        for sid, s in STOCKS.items():
            if a[0] in s["name"] or s["name"] in a[0]:
                ticker = sid
                break
        else:
            return f"没有这只股票：{a[0]}"

    s = STOCKS[ticker]
    price = state["prices"][ticker]
    holdings = state["holdings"].get(ticker, 0)
    fee = _fee_rate(state)

    if holdings == 0:
        return f"你手里没有 {s['name']}。"

    if len(a) >= 2 and a[1].lower() != "all":
        try:
            qty = min(int(a[1]), holdings)
        except:
            qty = holdings
    else:
        qty = holdings

    proceeds = round(price * qty * (1 - fee), 2)
    state["cash"] = round(state["cash"] + proceeds, 2)
    state["holdings"][ticker] -= qty
    if state["holdings"][ticker] == 0:
        state["cost_basis"][ticker] = 0.0

    cb = state["cost_basis"].get(ticker, 0)
    pnl = (price - cb) * qty
    if pnl >= 0:
        state["stats"]["profitable_trades"] += 1
    else:
        state["stats"]["losing_trades"] += 1
    state["stats"]["total_trading_volume"] += proceeds
    state["stats"]["total_fees_paid"] += price * qty - proceeds

    # 检查抄底交易
    if state["stats"]["crashes_survived"] > 0 and state.get("_crash_day"):
        crash_day = state.get("_crash_day", 0)
        if crash_day > 0:
            buy_logs = [t for t in state["trades_log"] if t[1] == "BUY" and t[2] == ticker and t[0] >= crash_day]
            if buy_logs and pnl > 0 and pnl / (cb * qty) > 0.2 if cb > 0 else False:
                state["stats"]["successful_dip_trades"] += 1

    state["trades_log"].append((state["day"], "SELL", ticker, qty, price))
    state["turn"] += 1

    pnl_emoji = "💰" if pnl >= 0 else "💸"
    _tick(state)
    _save(state)

    if state["holdings"][ticker] == 0:
        return f"{pnl_emoji} 清仓 {s['name']} {qty} 股 @ {price:.2f}，到手 {proceeds:.0f} 元。盈亏 {pnl:+.0f} 元。"
    return f"{pnl_emoji} 卖出 {s['name']} {qty} 股 @ {price:.2f}，到手 {proceeds:.0f} 元。剩 {state['holdings'][ticker]} 股。"


def _cmd_bid(state, a):
    if len(a) < 3:
        return "格式：bid <股名> <价格> <股数>  如 bid nebula 75 10"
    ticker = a[0].lower()
    if ticker not in STOCKS:
        for sid in STOCKS:
            if a[0] in STOCKS[sid]["name"]:
                ticker = sid
                break
        else:
            return f"没有这只股票：{a[0]}"
    try:
        price = float(a[1])
        qty = int(a[2])
    except:
        return "价格和股数得是数字。如 bid nebula 75 10"

    if qty <= 0 or price <= 0:
        return "价格和股数必须大于 0。"

    # 预留资金
    fee = _fee_rate(state)
    estimated_cost = round(price * qty * (1 + fee), 2)
    if estimated_cost > state["cash"]:
        return f"资金不足以挂单。预估成本 {estimated_cost:.0f}，你只有 {state['cash']:.0f}。"

    oid = state["next_order_id"]
    state["next_order_id"] += 1
    state["pending_orders"].append({
        "id": oid, "type": "bid", "ticker": ticker,
        "price": price, "qty": qty, "placed_day": state["day"]
    })
    # 预留资金
    state["cash"] = round(state["cash"] - estimated_cost, 2)
    state["_reserved_cash"] = state.get("_reserved_cash", 0) + estimated_cost
    state["turn"] += 1
    _tick(state)
    _save(state)
    return f"📝 限价买单已挂：{STOCKS[ticker]['name']} {qty}股 @ {price:.2f}（冻结 {estimated_cost:.0f} 元）"


def _cmd_ask(state, a):
    if len(a) < 3:
        return "格式：ask <股名> <价格> <股数>  如 ask nebula 95 5"
    ticker = a[0].lower()
    if ticker not in STOCKS:
        for sid in STOCKS:
            if a[0] in STOCKS[sid]["name"]:
                ticker = sid
                break
        else:
            return f"没有这只股票：{a[0]}"
    try:
        price = float(a[1])
        qty = int(a[2])
    except:
        return "价格和股数得是数字。"

    holdings = state["holdings"].get(ticker, 0)
    if qty > holdings:
        return f"持仓不足。你只有 {holdings} 股 {STOCKS[ticker]['name']}。"

    oid = state["next_order_id"]
    state["next_order_id"] += 1
    state["pending_orders"].append({
        "id": oid, "type": "ask", "ticker": ticker,
        "price": price, "qty": qty, "placed_day": state["day"]
    })
    # 冻结持仓
    state["holdings"][ticker] -= qty
    state["_reserved_holdings"] = state.get("_reserved_holdings", {})
    state["_reserved_holdings"][ticker] = state["_reserved_holdings"].get(ticker, 0) + qty
    state["turn"] += 1
    _tick(state)
    _save(state)
    return f"📝 限价卖单已挂：{STOCKS[ticker]['name']} {qty}股 @ {price:.2f}"


def _cmd_orders(state):
    orders = state.get("pending_orders", [])
    if not orders:
        return "📝 当前没有待成交的订单。"
    lines = ["📝 【待成交订单】"]
    for o in orders:
        typ = "🟢 限价买" if o["type"] == "bid" else "🔴 限价卖"
        sname = STOCKS[o["ticker"]]["name"]
        cur_px = state["prices"][o["ticker"]]
        lines.append(f"  #{o['id']} {typ} {sname} {o['qty']}股 @ {o['price']:.2f}（现价 {cur_px:.2f}）· 挂于第{o['placed_day']}天")
    return "\n".join(lines)


def _cmd_cancel(state, a):
    if len(a) < 1:
        return "格式：cancel <股名> [all]  取消该股票的所有限价单"
    ticker = a[0].lower()
    if ticker not in STOCKS:
        for sid in STOCKS:
            if a[0] in STOCKS[sid]["name"]:
                ticker = sid
                break
        else:
            return f"没有这只股票：{a[0]}"

    orders = state.get("pending_orders", [])
    to_cancel = [o for o in orders if o["ticker"] == ticker]
    if not to_cancel:
        return f"没有 {STOCKS[ticker]['name']} 的待成交订单。"

    for o in to_cancel:
        if o["type"] == "bid":
            fee = _fee_rate(state)
            refund = round(o["price"] * o["qty"] * (1 + fee), 2)
            state["cash"] = round(state["cash"] + refund, 2)
            state["_reserved_cash"] = state.get("_reserved_cash", 0) - refund
        else:
            qty = o["qty"]
            state["holdings"][ticker] = state["holdings"].get(ticker, 0) + qty
            reserved = state.get("_reserved_holdings", {})
            reserved[ticker] = reserved.get(ticker, 0) - qty

    state["pending_orders"] = [o for o in orders if o["ticker"] != ticker]
    _save(state)
    return f"❌ 已取消 {STOCKS[ticker]['name']} 的 {len(to_cancel)} 个订单。资金/持仓已退回。"


def _cmd_wait(state, a):
    cnt = 1
    if a:
        try:
            cnt = min(int(a[0]), 60)
        except:
            cnt = 1
    if cnt < 1:
        cnt = 1

    all_events = []
    for _ in range(cnt):
        events = _tick(state)
        all_events.extend(events)

    lines = [f"⏳ 等了 {cnt} 个交易日（第 {state['day']-cnt+1} → {state['day']} 天）"]

    # 价格摘要（按板块）
    for sec_id, sec in SECTORS.items():
        sec_stocks = [(sid, s) for sid, s in STOCKS.items() if s["sector"] == sec_id]
        for sid, s in sec_stocks:
            hist = state["prices_history"][sid]
            if len(hist) > cnt:
                start = hist[-(cnt+1)]
                end = hist[-1]
                chg = end - start
                pct = chg / start * 100
                arrow = "📈" if chg >= 0 else "📉"
                lines.append(f"  {arrow} {s['name']}：{start:.1f} → {end:.1f}（{pct:+.1f}%）")

    # 重要事件（去重，但月度考核始终保留）
    seen = set()
    monthly_events = []
    other_events = []
    for ev in all_events:
        if "考核" in ev[1] and ("月度" in ev[1] or "季度" in ev[1] or "结算" in ev[1]):
            monthly_events.append(ev)
        else:
            key = ev[1][:40]
            if key not in seen:
                seen.add(key)
                other_events.append(ev)
    # 先显示月结
    for emoji, msg in monthly_events:
        lines.append(f"  {emoji} {msg}")
    # 再显示其他重要事件
    for emoji, msg in other_events[-4:]:
        lines.append(f"  {emoji} {msg}")

    nw_val = _nw(state)
    pnl = nw_val - _start_cash(state)
    ret = round(pnl / _start_cash(state) * 100, 1)
    bench_nw = state["benchmark_history"][-1] if state["benchmark_history"] else 1000
    vs_bench = nw_val - bench_nw
    vs_str = f"跑赢大盘 {vs_bench:+.0f}" if vs_bench >= 0 else f"跑输大盘 {vs_bench:.0f}"
    lines.append(f"  净值：{nw_val:.0f} 元（{pnl:+.0f} · {ret:+.1f}%）vs ETF基准：{bench_nw:.0f}（{vs_str}）")

    # 情感化心情
    if sum(state["holdings"].get(sid, 0) for sid in STOCKS) > 0 or state.get("predictions"):
        mood = _emotion_line(state)
        if mood:
            lines.append(f"\n💭 {mood}")

    _save(state)
    return "\n".join(lines)


def _cmd_news(state):
    log = state.get("news_log", [])
    if not log:
        return "📰 近期没有重大新闻。"
    lines = ["📰 【近期市场新闻】"]
    for day, kind, target, msg in log[-10:]:
        kind_label = {"pos": "利好", "neg": "利空", "macro": "宏观", "sector": "板块"}.get(kind, kind)
        lines.append(f"  (第{day}天) [{kind_label}] {msg}")
    return "\n".join(lines)


def _cmd_look(state, a):
    if not a:
        return "格式：look <股名>  如 look nebula"
    ticker = a[0].lower()
    if ticker not in STOCKS:
        for sid, s in STOCKS.items():
            if a[0] in s["name"] or s["name"] in a[0]:
                ticker = sid
                break
        else:
            return f"没找到：{a[0]}"

    s = STOCKS[ticker]
    price = state["prices"][ticker]
    hist = state["prices_history"][ticker]
    sec = SECTORS[s["sector"]]
    cycle = MARKET_CYCLES[state["market_cycle"]]

    total_chg = price - hist[0]
    total_pct = total_chg / hist[0] * 100 if hist[0] > 0 else 0

    lines = [
        f"🔍 【{s['name']}】（{s['code']}）",
        f"板块：{sec['emoji']} {sec['name']}  {'🔥热门' if state['hot_sector'] == s['sector'] else '❄️冷门' if state['cold_sector'] == s['sector'] else ''}",
        f"{s['desc']}",
        f"现价：{price:.2f} ｜ 总变动：{total_chg:+.1f}（{total_pct:+.1f}%）",
        f"波动率：{s['vol']*100:.0f}% ｜ Beta：{s['beta']} ｜ 标签：{' · '.join(s['tags'])}",
        f"",
    ]

    recent = hist[-12:] if len(hist) >= 12 else hist
    if len(recent) > 1:
        bars = _bar_chart(recent)
        lines.append(f"📉 近期走势（{len(recent)}日）：")
        for i, bar in enumerate(bars):
            idx = len(hist) - len(recent) + i + 1
            lines.append(f"  D{idx:>3d}: {bar} {recent[i]:.1f}")

    holdings = state["holdings"].get(ticker, 0)
    reserved = state.get("_reserved_holdings", {}).get(ticker, 0)
    if holdings > 0 or reserved > 0:
        cb = state["cost_basis"].get(ticker, 0)
        pos_pnl = (price - cb) * (holdings + reserved)
        lines.append(f"")
        lines.append(f"📋 持仓：{holdings}股{'（冻结' + str(reserved) + '股）' if reserved > 0 else ''} @ {cb:.1f}  浮动盈亏：{pos_pnl:+.0f} 元")

    return "\n".join(lines)


def _cmd_history(state):
    nw = state["net_worth_history"]
    bench = state["benchmark_history"]
    lines = ["📈 【净值曲线 vs 大盘】"]

    start, end = nw[0], nw[-1]
    max_nw, min_nw = max(nw), min(nw)
    ret = (end - start) / start * 100 if start > 0 else 0
    bench_ret = (bench[-1] - bench[0]) / bench[0] * 100 if bench[0] > 0 else 0

    lines.append(f"  你的净值：{start:.0f} → {end:.0f}（{ret:+.1f}%）最高 {max_nw:.0f} 最低 {min_nw:.0f}")
    lines.append(f"  ETF基准：{bench[0]:.0f} → {bench[-1]:.0f}（{bench_ret:+.1f}%）")
    lines.append(f"  vs基准：{(ret - bench_ret):+.1f}%  {'👑跑赢' if ret >= bench_ret else '😅跑输'}")

    if len(nw) > 1:
        combined = nw + bench
        mn, mx = min(combined), max(combined)
        rng = max(mx - mn, 0.01)
        width = 20
        step = max(1, len(nw) // 10)
        lines.append(f"\n  时间线（每{step}天）：你 ██ vs ETF ··")
        for i in range(0, len(nw), step):
            v = nw[i]
            b = bench[i] if i < len(bench) else bench[-1]
            bar_nw = int((v - mn) / rng * width)
            bar_b = int((b - mn) / rng * width)
            # 交错显示
            nw_line = "█" * bar_nw
            bench_line = "▓" * bar_b
            lines.append(f"  D{i+1:>3d}: {nw_line}{'·' * (width - bar_nw)} {v:.0f}")
            if i < len(nw) - step:
                lines.append(f"       {bench_line}{'·' * (width - bar_b)} {b:.0f}")

    # 最近交易
    trades = state.get("trades_log", [])
    if trades:
        lines.append(f"\n📋 最近交易：")
        for day, typ, ticker, qty, price in trades[-5:]:
            sname = STOCKS[ticker]["name"]
            typ_sym = "🟢" if "BUY" in typ else "🔴"
            lines.append(f"  第{day}天 {typ_sym} {sname} {qty}股 @ {price:.2f}")

    return "\n".join(lines)


def _cmd_research(state, a):
    if not a:
        return "格式：research <股名>  如 research nebula（消耗1个交易日）"
    ticker = a[0].lower()
    if ticker not in STOCKS:
        for sid, s in STOCKS.items():
            if a[0] in s["name"] or s["name"] in a[0]:
                ticker = sid
                break
        else:
            return f"没找到：{a[0]}"

    s = STOCKS[ticker]
    price = state["prices"][ticker]
    rng = _rng(state)
    rank = _trader_rank(state)
    noise = max(0.02, 0.15 - rank * 0.01)  # 等级越高噪声越小

    # 估值范围（带噪声）
    fair_low = round(s["base"] * (0.85 + noise * (rng.random() - 0.5)), 1)
    fair_high = round(s["base"] * (1.15 + noise * (rng.random() - 0.5)), 1)

    # 动量判断
    hist = state["prices_history"][ticker]
    if len(hist) >= 5:
        recent_ret = (hist[-1] - hist[-5]) / hist[-5]
        if recent_ret > 0.05:
            momentum = "强势上涨 📈"
        elif recent_ret > 0.01:
            momentum = "温和上涨 ↗️"
        elif recent_ret > -0.01:
            momentum = "横盘整理 ➡️"
        elif recent_ret > -0.05:
            momentum = "温和下跌 ↘️"
        else:
            momentum = "加速下跌 📉"
    else:
        momentum = "数据不足"

    # 板块前景
    sec = SECTORS[s["sector"]]
    is_hot = state["hot_sector"] == s["sector"]
    is_cold = state["cold_sector"] == s["sector"]
    outlook = "🔥 板块当前热门，资金流入" if is_hot else ("❄️ 板块当前冷门，资金流出" if is_cold else "📊 板块表现中性")
    days_to_rotation = state["next_rotation_day"] - state["day"]
    rotation_hint = f"板块轮动约在 {max(0, days_to_rotation)} 天后" if days_to_rotation > 0 else "板块轮动即将到来"

    # 风险评估
    risk_level = "高风险" if s["vol"] * s["beta"] > 0.12 else ("中等风险" if s["vol"] * s["beta"] > 0.06 else "低风险")

    _tick(state)  # 研究消耗1天
    _update_rng(state, rng)
    _save(state)

    return (
        f"🔬 【深度研究：{s['name']}】\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 估值区间：{fair_low} ~ {fair_high} 元（现价 {price:.2f}）\n"
        f"   {'⚠️ 高估' if price > fair_high else '💎 低估' if price < fair_low else '✅ 合理'}\n"
        f"📈 动量：{momentum}\n"
        f"🏭 板块：{sec['emoji']} {sec['name']} — {outlook}\n"
        f"   {rotation_hint}\n"
        f"⚡ 风险：{risk_level}（波动率 {s['vol']*100:.0f}%，Beta {s['beta']}）\n"
        f"   {'该股波动极大，不适合重仓' if s['vol'] * s['beta'] > 0.12 else '波动适中，适合波段操作' if s['vol'] * s['beta'] > 0.06 else '波动较低，适合长期持有'}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💡 研究精度：{100-noise*100:.0f}%（交易员等级 {rank}）"
    )


def _cmd_sector_info(state, a):
    if not a:
        # 列出所有板块
        lines = ["🏭 【板块概览】"]
        for sec_id, sec in SECTORS.items():
            hot_mark = " 🔥热门" if state["hot_sector"] == sec_id else (" ❄️冷门" if state["cold_sector"] == sec_id else "")
            stocks_in_sec = [s for s in STOCKS.values() if s["sector"] == sec_id]
            avg_px = sum(state["prices"][sid] for sid, s in STOCKS.items() if s["sector"] == sec_id) / len(stocks_in_sec) if stocks_in_sec else 0
            lines.append(f"  {sec['emoji']} {sec['name']}{hot_mark} — {sec['desc']}")
            lines.append(f"    成分股：{' · '.join(s['name'] for s in stocks_in_sec)}")
            lines.append(f"    板块均价：{avg_px:.1f}")
        lines.append(f"\n  下次轮动：约 {max(0, state['next_rotation_day'] - state['day'])} 天后")
        return "\n".join(lines)

    sec_id = a[0].lower()
    if sec_id not in SECTORS:
        for sid, sec in SECTORS.items():
            if a[0] in sec["name"]:
                sec_id = sid
                break
        else:
            return f"没有这个板块。可选：tech/cons/ener/fin"

    sec = SECTORS[sec_id]
    is_hot = state["hot_sector"] == sec_id
    is_cold = state["cold_sector"] == sec_id
    lines = [
        f"🏭 【{sec['emoji']} {sec['name']}板块分析】",
        f"{sec['desc']}",
        f"状态：{'🔥 当前热门' if is_hot else '❄️ 当前冷门' if is_cold else '📊 表现中性'}",
        f"",
    ]
    for sid, s in STOCKS.items():
        if s["sector"] != sec_id:
            continue
        price = state["prices"][sid]
        hist = state["prices_history"][sid]
        chg_5d = (price - hist[-5]) / hist[-5] * 100 if len(hist) >= 5 else 0
        lines.append(f"  {s['name']}({s['code']}) {price:.2f}  5日: {chg_5d:+.1f}%  {s['desc'][:30]}...")

    return "\n".join(lines)


def _cmd_sentiment(state):
    cycle = MARKET_CYCLES[state["market_cycle"]]
    rng = _rng(state)

    nw_hist = state["net_worth_history"]
    if len(nw_hist) >= 10:
        recent_ret = (nw_hist[-1] - nw_hist[-10]) / nw_hist[-10] if nw_hist[-10] > 0 else 0
    else:
        recent_ret = 0

    # 涨跌比
    up_count = 0
    for sid in STOCKS:
        hist = state["prices_history"][sid]
        if len(hist) >= 2 and hist[-1] > hist[-2]:
            up_count += 1
    breadth = up_count / len(STOCKS)

    fear_greed = int(50 + recent_ret * 500 + (breadth - 0.5) * 40)
    fear_greed = max(0, min(100, fear_greed))

    if fear_greed >= 80:
        fg_label = "极度贪婪 😈"
    elif fear_greed >= 60:
        fg_label = "偏向贪婪 😊"
    elif fear_greed >= 40:
        fg_label = "中性 😐"
    elif fear_greed >= 20:
        fg_label = "偏向恐惧 😨"
    else:
        fg_label = "极度恐惧 💀"

    bar = "█" * int(fear_greed / 5) + "·" * (20 - int(fear_greed / 5))

    return (
        f"🎭 【市场情绪】\n"
        f"恐惧/贪婪指数：{fear_greed} — {fg_label}\n"
        f"  0 {bar} 100\n"
        f"上涨家数：{up_count}/{len(STOCKS)}（{breadth*100:.0f}%）\n"
        f"市场状态：{cycle['emoji']} {cycle['name']}\n"
        f"10日回报：{recent_ret*100:+.1f}%\n"
        f"\n💡 {cycle['vibe']}"
    )


def _cmd_cycle(state):
    cycle = MARKET_CYCLES[state["market_cycle"]]
    transitions = cycle["transitions"]

    lines = [
        f"🔄 【市场周期分析】",
        f"当前：{cycle['emoji']} {cycle['name']}（已持续 {state['cycle_day']} 天）",
        f"{cycle['vibe']}",
        f"典型持续时间：{cycle['min_days']}~{cycle['max_days']} 天",
        f"",
        f"可能转换方向：",
    ]
    for next_id, prob in transitions.items():
        next_cycle = MARKET_CYCLES[next_id]
        bar = "█" * int(prob * 40) + "·" * (40 - int(prob * 40))
        lines.append(f"  → {next_cycle['emoji']} {next_cycle['name']}：{prob*100:.0f}% {bar}")

    lines.append(f"")
    lines.append(f"下次板块轮动：约 {max(0, state['next_rotation_day'] - state['day'])} 天后")

    return "\n".join(lines)


def _cmd_watch(state, a, add):
    if not a:
        return "格式：watch <股名> 或 unwatch <股名>"
    ticker = a[0].lower()
    if ticker not in STOCKS:
        for sid, s in STOCKS.items():
            if a[0] in s["name"]:
                ticker = sid
                break
        else:
            return f"没找到：{a[0]}"

    wl = state.get("watchlist", [])
    if add:
        if ticker in wl:
            return f"{STOCKS[ticker]['name']} 已在关注列表中。"
        wl.append(ticker)
        state["watchlist"] = wl
        return f"👀 已关注 {STOCKS[ticker]['name']}。"
    else:
        if ticker not in wl:
            return f"{STOCKS[ticker]['name']} 不在关注列表中。"
        wl.remove(ticker)
        state["watchlist"] = wl
        return f"已取消关注 {STOCKS[ticker]['name']}。"


def _cmd_watchlist(state):
    wl = state.get("watchlist", [])
    if not wl:
        return "👀 关注列表为空。用 watch <股名> 添加。"
    lines = ["👀 【关注列表】"]
    for ticker in wl:
        s = STOCKS[ticker]
        price = state["prices"][ticker]
        hist = state["prices_history"][ticker]
        chg = price - hist[-2] if len(hist) >= 2 else 0
        pct = chg / hist[-2] * 100 if len(hist) >= 2 else 0
        arrow = "📈" if chg >= 0 else "📉"
        holdings = state["holdings"].get(ticker, 0)
        pos = f" 💼{holdings}股" if holdings > 0 else ""
        lines.append(f"  {arrow} {s['name']} {price:.2f} {pct:+.1f}%{pos}")
    return "\n".join(lines)


def _cmd_pnl(state):
    lines = ["💰 【盈亏拆解】"]
    total_pnl = 0
    for sid in STOCKS:
        sh = state["holdings"].get(sid, 0)
        if sh == 0:
            continue
        cb = state["cost_basis"].get(sid, 0)
        px = state["prices"][sid]
        pnl = (px - cb) * sh
        pnl_pct = (px - cb) / cb * 100 if cb > 0 else 0
        total_pnl += pnl
        icon = "📈" if pnl >= 0 else "📉"
        lines.append(f"  {icon} {STOCKS[sid]['name']}：{pnl:+.0f} 元（{pnl_pct:+.1f}%）— {sh}股 @ {cb:.1f}→{px:.1f}")

    # 已平仓盈亏
    realized = _nw(state) - 1000.0 - total_pnl
    lines.append(f"  ───────")
    lines.append(f"  未实现盈亏：{total_pnl:+.0f} 元")
    lines.append(f"  已实现盈亏：{realized:+.0f} 元")
    lines.append(f"  手续费用：{state['stats']['total_fees_paid']:.1f} 元")

    return "\n".join(lines)


def _cmd_trades(state):
    trades = state.get("trades_log", [])
    if not trades:
        return "📋 还没有交易记录。"
    lines = ["📋 【最近交易】"]
    for day, typ, ticker, qty, price in trades[-15:]:
        sname = STOCKS[ticker]["name"]
        typ_sym = "🟢买入" if "BUY" in typ else "🔴卖出"
        lines.append(f"  第{day:>3d}天 {typ_sym} {sname} {qty}股 @ {price:.2f}")
    return "\n".join(lines)


def _cmd_titles(state):
    earned = state.get("titles_earned", {})
    if not earned:
        return "🏆 还没有获得任何称号。开始交易吧！"
    lines = [f"🏆 【已获称号】交易员等级 {_trader_rank(state)}"]
    for tid, td in earned.items():
        tdef = TITLES.get(tid)
        if not tdef:
            continue
        p = td.get("prestige", 0)
        p_str = f" Lv.{p}" if p > 0 else ""
        perk = tdef.get("perk")
        perk_str = ""
        if perk:
            parts = []
            if "fee_discount" in perk:
                parts.append(f"手续费-{perk['fee_discount']*100:.1f}%")
            if "research_bonus" in perk:
                parts.append(f"研究精度+{perk['research_bonus']*100:.0f}%")
            if "crash_resist" in perk:
                parts.append(f"崩盘抗性+{perk['crash_resist']*100:.0f}%")
            if "sector_boost" in perk:
                parts.append(f"{SECTORS[perk['sector_boost']]['name']}板块加成")
            if "idle_interest" in perk:
                parts.append(f"空仓利息+{perk['idle_interest']*100:.1f}%/日")
            if "news_early" in perk:
                parts.append(f"新闻提前{perk['news_early']}天")
            perk_str = " · ".join(parts)
        lines.append(f"  {tdef['icon']} {tdef['name']}{p_str} — {tdef['desc']}")
        if perk_str:
            lines.append(f"     福利：{perk_str}")

    # 下一个财富称号进度
    for tid in ["wanyuan", "zibenjia", "zhishang"]:
        tdef = TITLES.get(tid)
        if not tdef:
            continue
        current = earned.get(tid)
        if tdef.get("prestige_at"):
            lv = (current.get("prestige", 0) + 1) if current else 1
            threshold = tdef["prestige_at"](lv - 1 if current else 0)
            if current is None:
                threshold = tdef["prestige_at"](0)
            nw_val = _nw(state)
            if nw_val < threshold * 5:  # 差距不超过5倍才显示
                pct = nw_val / threshold * 100
                lines.append(f"\n  🎯 距离{tdef['icon']}{tdef['name']}：{nw_val:.0f}/{threshold:.0f}（{pct:.0f}%）")
    return "\n".join(lines)


def _cmd_achievements(state):
    earned = state.get("titles_earned", {})
    lines = ["🏅 【称号进度】"]

    earned_count = 0
    total_count = len(TITLES)

    for tid, tdef in TITLES.items():
        has_it = tid in earned
        if has_it:
            earned_count += 1
            p = earned[tid].get("prestige", 0)
            p_str = f" Lv.{p}" if p > 0 else ""
            lines.append(f"  ✅ {tdef['icon']} {tdef['name']}{p_str} — {tdef['desc']}")
        else:
            lines.append(f"  🔒 {tdef['icon']} {tdef['name']} — {tdef['desc']}")

    lines.insert(1, f"进度：{earned_count}/{total_count}（{earned_count*100//total_count}%）")
    lines.append(f"\n💡 交易员等级 {_trader_rank(state)} = 所有称号等级之和")
    return "\n".join(lines)


def _cmd_compare(state):
    nw_val = _nw(state)
    bench_nw = state["benchmark_history"][-1] if state["benchmark_history"] else 1000
    diff = nw_val - bench_nw
    ret = (nw_val - 1000.0) / 1000.0 * 100
    bench_ret = (bench_nw - 1000.0) / 1000.0 * 100

    lines = [
        f"⚖️ 【绩效对比】",
        f"  你的净值：{nw_val:.0f} 元（{ret:+.1f}%）",
        f"  ETF基准：{bench_nw:.0f} 元（{bench_ret:+.1f}%）",
        f"  超额收益：{diff:+.0f} 元（{ret - bench_ret:+.1f}%）",
    ]

    if diff > 0:
        lines.append(f"  👑 你跑赢了大盘！选股和择时能力获得了回报。")
    elif diff < 0:
        lines.append(f"  😅 你跑输了大盘。也许直接买 ETF 更省心？")
    else:
        lines.append(f"  🤝 刚好和大盘持平。")

    # 统计
    stats = state["stats"]
    lines.append(f"\n📊 【交易统计】")
    lines.append(f"  最大净值：{stats['max_nw']:.0f} 元")
    lines.append(f"  最小净值：{stats['min_nw']:.0f} 元")
    lines.append(f"  最大回撤：{stats['max_drawdown']*100:.1f}%")
    lines.append(f"  盈利交易：{stats['profitable_trades']} 次")
    lines.append(f"  亏损交易：{stats['losing_trades']} 次")
    win_rate = stats['profitable_trades'] / max(1, stats['profitable_trades'] + stats['losing_trades']) * 100
    lines.append(f"  胜率：{win_rate:.0f}%")
    lines.append(f"  总手续费：{stats['total_fees_paid']:.1f} 元")

    return "\n".join(lines)


# ═══════════════════════════════════════════
# ── 新游戏 ──
# ═══════════════════════════════════════════
def new_game(seed=None, career="retail"):
    global _SEED
    if seed is not None:
        _SEED = seed
    career_cfg = CAREERS.get(career, CAREERS["retail"])
    # 基金经理需要解锁检查
    if career != "retail" and career_cfg.get("unlock_rank", 0) > 0:
        # 通过API调用时允许直接创建（用户主动选择）
        pass
    rng = _Rng(_SEED)
    state = _default_state(rng, career)
    _save(state)
    icon = career_cfg["icon"]
    name = career_cfg["name"]
    cash = career_cfg["start_cash"]
    return f"🔄 新局已开（{icon}{name} · 种子 {_SEED:#x} · 本金 {cash} 元）。\n{career_cfg['desc']}\n目标：不断提升交易员等级。市场永远在变。"


# ═══════════════════════════════════════════
# ── 预测系统 ──
# ═══════════════════════════════════════════
def _cmd_predict(state, a):
    if len(a) < 2:
        return "格式：predict <股名> <涨/跌> [天数默认5]  如 predict nebula 涨 5"
    ticker = a[0].lower()
    if ticker not in STOCKS:
        for sid, s in STOCKS.items():
            if a[0] in s["name"] or s["name"] in a[0]:
                ticker = sid
                break
        else:
            return f"没有这只股票：{a[0]}"

    direction = a[1]
    if direction not in ("涨", "跌", "up", "down"):
        return "方向用「涨」或「跌」。如 predict nebula 涨 5"

    is_up = direction in ("涨", "up")
    days = int(a[2]) if len(a) >= 3 else 5
    days = max(1, min(days, 20))

    price_now = state["prices"][ticker]
    pred = {
        "ticker": ticker,
        "direction": "up" if is_up else "down",
        "start_price": price_now,
        "start_day": state["day"],
        "deadline_day": state["day"] + days,
        "resolved": False,
    }
    if "predictions" not in state:
        state["predictions"] = []
    state["predictions"].append(pred)
    state["turn"] += 1
    tick_events = _tick(state)
    _save(state)

    # 捕获tick中结算的预测事件
    dir_word = "涨" if is_up else "跌"
    lines = [f"🔮 预测已记录：{STOCKS[ticker]['name']} 将在 {days} 天内上{dir_word}（现价 {price_now:.2f}，第{state['day']}天验证）。"]
    for emoji, msg in tick_events:
        if "预测" in msg or "预言" in msg or "章鱼" in msg:
            lines.append(f"  {emoji} {msg}")
    return "\n".join(lines)


def _resolve_predictions(state):
    """检查到期的预测，结算分数。对的生成叙事，错的沉默入日记。"""
    events = []
    for p in state.get("predictions", []):
        if p.get("resolved"):
            continue
        if state["day"] < p["deadline_day"]:
            continue
        p["resolved"] = True
        px = state["prices"].get(p["ticker"], p["start_price"])
        is_flat = abs(px - p["start_price"]) < 0.01
        actual_up = px > p["start_price"]
        predicted_up = p["direction"] == "up"
        is_correct = actual_up == predicted_up if not is_flat else None  # None = 平局

        state.setdefault("predict_correct", 0)
        state.setdefault("predict_total", 0)
        state.setdefault("predict_score", 0)
        state.setdefault("predict_streak", 0)

        state["predict_total"] += 1
        sname = STOCKS[p["ticker"]]["name"]
        chg = (px - p["start_price"]) / p["start_price"] * 100

        if is_correct is None:
            # 平局：不奖不罚
            _add_journal(state, "🔮", f"预测{sname}{'涨' if predicted_up else '跌'}，纹丝不动。平局，不扣分。")
        elif is_correct:
            state["predict_correct"] += 1
            state["predict_streak"] = state.get("predict_streak", 0) + 1
            state["predict_score"] += 3

            # 叙事增强
            idx = hash(f"glory_{state['day']}_{p['ticker']}") % len(_PREDICT_GLORY)
            glory = _PREDICT_GLORY[idx].format(name=sname)
            events.append(("📰", f"预测命中！{sname} {chg:+.1f}%，+3分。{glory}"))

            # 连续预测正确称号
            streak = state["predict_streak"]
            if streak in _PREDICT_STREAK_TITLES:
                tid_name, icon, desc = _PREDICT_STREAK_TITLES[streak]
                tid = f"predict_streak_{streak}"
                if tid not in state.get("titles_earned", {}):
                    state["titles_earned"][tid] = {"day": state["day"], "prestige": 0}
                    state.setdefault("new_titles", []).append(tid)
                    events.append(("🏆", f"解锁称号：{icon}{tid_name} —— {desc}"))
        else:
            state["predict_streak"] = 0
            state["predict_score"] = max(0, state["predict_score"] - 1)
            # 错误不鞭尸，只记入日记
            _add_journal(state, "🔮", f"预测{sname}{'涨' if predicted_up else '跌'}，实际{chg:+.1f}%。没关系，市场永远是对的。")

    return events


# ═══════════════════════════════════════════
# ── 持仓日记 ──
# ═══════════════════════════════════════════
def _cmd_journal(state):
    entries = state.get("position_journal", [])
    lines = ["📔 【持仓心情日记】"]
    if not entries:
        lines.append("  还没有持仓日记。买了股票之后才有故事。")
    for day, mood, text in entries[-12:]:
        lines.append(f"  第{day:>3d}天 {mood} {text}")

    # 当前持仓的心情总结
    nw_val = _nw(state)
    pnl = nw_val - _start_cash(state)
    if pnl > 100:
        lines.append(f"\n  💭 当前心情：{nw_val:.0f}元（+{pnl:.0f}）—— 春风得意马蹄疾")
    elif pnl > 0:
        lines.append(f"\n  💭 当前心情：{nw_val:.0f}元（+{pnl:.0f}）—— 小赚也是赚")
    elif pnl > -100:
        lines.append(f"\n  💭 当前心情：{nw_val:.0f}元（{pnl:.0f}）—— 还在扛着")
    elif pnl > -500:
        lines.append(f"\n  💭 当前心情：{nw_val:.0f}元（{pnl:.0f}）—— 已经麻了")
    else:
        lines.append(f"\n  💭 当前心情：{nw_val:.0f}元（{pnl:.0f}）—— 删软件了")

    # 套牢榜
    bagholds = []
    for sid in STOCKS:
        sh = state["holdings"].get(sid, 0)
        if sh > 0:
            cb = state["cost_basis"].get(sid, 0)
            px = state["prices"].get(sid, 0)
            if cb > 0 and px < cb:
                loss_pct = (px - cb) / cb * 100
                days_held = state["stats"]["hold_days_current"].get(sid, 0)
                bagholds.append((STOCKS[sid]["name"], loss_pct, days_held))
    if bagholds:
        lines.append(f"\n  ⛓️ 套牢榜：")
        for name, lp, dh in sorted(bagholds, key=lambda x: x[1]):
            lines.append(f"    {name}：{lp:.0f}%，已扛{dh}天")

    # 预测记录
    preds = [p for p in state.get("predictions", []) if not p.get("resolved")]
    if preds:
        lines.append(f"\n  🔮 待验证预测：{len(preds)} 条")
        for p in preds[-3:]:
            dir_word = "涨" if p["direction"] == "up" else "跌"
            remaining = p["deadline_day"] - state["day"]
            lines.append(f"    {STOCKS[p['ticker']]['name']} 看{dir_word}（剩{remaining}天）")
    score = state.get("predict_score", 0)
    correct = state.get("predict_correct", 0)
    total = state.get("predict_total", 0)
    if total > 0:
        lines.append(f"  预测得分：{score}分（{correct}/{total} 正确，准确率 {correct*100//max(1,total)}%）")

    return "\n".join(lines)


def _add_journal(state, mood, text):
    if "position_journal" not in state:
        state["position_journal"] = []
    state["position_journal"].append((state["day"], mood, text))
    if len(state["position_journal"]) > 80:
        state["position_journal"] = state["position_journal"][-80:]


# ═══════════════════════════════════════════
# ── 月度结算 ──
# ═══════════════════════════════════════════
def _monthly_settlement(state):
    """每月结算：考核跑赢大盘能力，压力而非收费"""
    state["last_settlement_day"] = state["day"]
    nw_val = _nw(state)
    month_num = state["day"] // 30

    prev_records = state.get("monthly_records", [])
    prev_nw = prev_records[-1]["end_nw"] if prev_records else 1000.0
    month_pnl = nw_val - prev_nw
    month_return = month_pnl / max(1, prev_nw) * 100

    # 对比 ETF 基准
    bench = state["benchmark_history"][-1] if state["benchmark_history"] else 1000
    bench_prev = state["benchmark_history"][-30] if len(state["benchmark_history"]) > 30 else 1000
    bench_return = (bench - bench_prev) / max(1, bench_prev) * 100
    alpha = month_return - bench_return  # 超额收益

    # 管理费（净值 0.1%，最低 2 元）
    mgmt_fee = max(2, round(nw_val * 0.001, 1))
    state["cash"] = round(state["cash"] - mgmt_fee, 2)
    state["stats"]["total_fees_paid"] += mgmt_fee

    # ── 考核评级（核心：跑赢大盘才算好）──
    if alpha >= 30:
        grade, grade_label, grade_icon = "S", "传奇", "👑"
    elif alpha >= 15:
        grade, grade_label, grade_icon = "A", "优秀", "🌟"
    elif alpha >= 5:
        grade, grade_label, grade_icon = "B", "良好", "📈"
    elif alpha >= 0:
        grade, grade_label, grade_icon = "C", "及格", "✅"
    elif alpha >= -10:
        grade, grade_label, grade_icon = "D", "观察", "⚠️"
    else:
        grade, grade_label, grade_icon = "F", "不合格", "💀"

    # 追踪连续不及格
    if grade in ("D", "F"):
        state["consecutive_loss_months"] = state.get("consecutive_loss_months", 0) + 1
    else:
        state["consecutive_loss_months"] = 0

    # 追踪连续跑赢
    if alpha > 0:
        if "consecutive_beat_months" not in state:
            state["consecutive_beat_months"] = 0
        state["consecutive_beat_months"] += 1
    else:
        state["consecutive_beat_months"] = 0

    record = {
        "month": month_num, "day": state["day"],
        "start_nw": prev_nw, "end_nw": nw_val, "pnl": month_pnl,
        "return": round(month_return, 1), "alpha": round(alpha, 1),
        "grade": grade, "mgmt_fee": mgmt_fee,
    }
    state["monthly_records"].append(record)
    if len(state["monthly_records"]) > 24:
        state["monthly_records"] = state["monthly_records"][-24:]

    events = []
    angel_total = state.get("angel_contributions", 0)
    rank = _trader_rank(state)

    # 结算报告
    is_quarterly = state.get("career") == "fund"
    label = "季度" if is_quarterly else "月度"
    lines = [
        f"第{month_num}次{label}考核（第{state['day']}天）",
        f"净值：{prev_nw:.0f} → {nw_val:.0f}（{month_return:+.1f}%）",
        f"ETF：{bench_return:+.1f}% | 超额收益：{alpha:+.1f}%",
        f"评级：{grade_icon} {grade_label}（{grade}级）| 管理费：-{mgmt_fee:.1f} 元",
    ]

    if angel_total > 0:
        total_return = (nw_val - 1000 - angel_total) / max(1, 1000 + angel_total) * 100
        lines.append(f"天使累计注资：{angel_total:.0f} 元 | 自有资金回报：{total_return:+.1f}%")

    # 考核后果
    consec_bad = state["consecutive_loss_months"]
    if consec_bad >= 3:
        lines.append(f"")
        lines.append(f"🔴 已连续 {consec_bad} 个月不及格！触发「被约谈」事件。")
        lines.append(f"👔 天使投资人：「你的业绩持续低于大盘，我需要看到改善，否则将撤回部分权限。」")
        # 可能降级称号
        if rank > 0 and state["day"] % 90 == 0:
            _demote_random_title(state)
            lines.append(f"⚠️ 一项称号等级被降级。")
    elif consec_bad >= 2:
        lines.append(f"⚠️ 连续 {consec_bad} 个月跑输大盘，请关注风险。")

    consec_beat = state.get("consecutive_beat_months", 0)
    if consec_beat >= 3:
        lines.append(f"")
        lines.append(f"👑 连续 {consec_beat} 个月跑赢大盘！你是真正的市场捕手。")
        if consec_beat == 3:
            if "market_beater" not in state.get("titles_earned", {}):
                state["titles_earned"]["market_beater"] = {"day": state["day"], "prestige": 0}
                state.setdefault("new_titles", []).append("market_beater")
                lines.append(f"🏆 解锁称号：📊跑赢大盘三连冠")

    if grade == "S":
        lines.append(f"🎆 传奇级表现！你的名字开始在投资圈流传。")

    events.append(("📋", "\n  ".join(lines)))
    return events


def _demote_random_title(state):
    """随机降级一个可降级的称号"""
    earned = state.get("titles_earned", {})
    demotable = [(tid, td) for tid, td in earned.items()
                 if TITLES.get(tid, {}).get("prestige_at") and td.get("prestige", 0) > 0]
    if demotable:
        idx = hash(f"{state['day']}_demote") % len(demotable)
        tid, td = demotable[idx]
        td["prestige"] = max(0, td["prestige"] - 1)
        if td["prestige"] == 0 and tid not in ["wanyuan", "zibenjia", "zhishang"]:
            del earned[tid]  # 非核心称号直接移除


# ═══════════════════════════════════════════
# ── 里程碑庆祝 ──
# ═══════════════════════════════════════════
def _check_celebrations(state):
    """检查是否触发庆祝事件"""
    # JSON反序列化后转回set
    ms = state.get("_celebrated_milestones")
    if isinstance(ms, list):
        state["_celebrated_milestones"] = set(ms)
    events = []
    nw_val = _nw(state)
    stats = state["stats"]

    # 净值创新高
    if nw_val > stats["max_nw"] * 1.01:
        milestone = _round_to_milestone(nw_val)
        if milestone and milestone not in state.get("_celebrated_milestones", set()):
            if "_celebrated_milestones" not in state:
                state["_celebrated_milestones"] = set()
            state["_celebrated_milestones"].add(milestone)
            events.append(("🎆", f"净值突破 {milestone} 元大关！新的里程碑！"))

    # 回本（从亏损回到盈利）
    if "was_profitable" not in state:
        state["was_profitable"] = False
    pnl = nw_val - 1000
    if pnl >= 0 and not state["was_profitable"]:
        state["was_profitable"] = True
        if state["day"] > 10:
            events.append(("🎉", "恭喜回本！从亏损的深渊爬回来了。"))

    if pnl < -200:
        state["was_profitable"] = False

    # 翻倍
    if nw_val >= 2000 and "celebrated_double" not in (state.get("_celebrated_milestones") or set()):
        if "_celebrated_milestones" not in state:
            state["_celebrated_milestones"] = set()
        state["_celebrated_milestones"].add("celebrated_double")
        events.append(("🚀", "资产翻倍！1000 变 2000，你是韭菜中的战斗机！"))

    # 十倍
    if nw_val >= 10000 and "celebrated_10x" not in (state.get("_celebrated_milestones") or set()):
        if "_celebrated_milestones" not in state:
            state["_celebrated_milestones"] = set()
        state["_celebrated_milestones"].add("celebrated_10x")
        events.append(("💎", "十倍收益！从散户到游资，你已经不是昨天的你了。"))

    return events


def _round_to_milestone(nw):
    for m in [200, 500, 1000, 1500, 2000, 3000, 5000, 10000, 20000, 50000, 100000, 500000, 1000000]:
        if abs(nw - m) / m < 0.02:
            return m
    return None


# ═══════════════════════════════════════════
# ── 预测叙事增强 ──
# ═══════════════════════════════════════════

_PREDICT_GLORY = [
    "投资社区开始流传：「有人提前看穿了{name}的走势。」你的发言被置顶了。",
    "散户群里有人@你：「哥，{name}真让你说中了，下只看什么？」",
    "一个自称「XX财经」的账号私信你，想采访你对{name}的判断逻辑。",
    "你的分析被截图转发到三个投资群。虽然他们不知道你是谁，但都管你叫「大佬」。",
    "隔壁老王听说你预测对了，暗示想跟单。你说「不构成投资建议」，但他还是跟了。",
    "你的预测记录被一个量化基金实习生注意到了。当然，他只是笑了笑。",
    "朋友圈里有人发：「感谢那位说{name}要涨的朋友，今晚加鸡腿。」你没点赞，但截了图。",
]

_PREDICT_STREAK_TITLES = {
    3: ("预言新星", "💫", "连续预测正确 3 次！散户群开始关注你的发言。"),
    7: ("市场先知", "🔮", "连续 7 次正确！有人怀疑你有内幕消息。"),
    15: ("章鱼附体", "🐙", "连续 15 次正确！你的每次发言都引发社区讨论。"),
}


def _handle_bankruptcy(state):
    """破产处理：平仓+救济金+称号"""
    # 清空所有持仓
    for sid in STOCKS:
        sh = state["holdings"].get(sid, 0)
        if sh > 0:
            px = state["prices"][sid]
            proceeds = round(px * sh * 0.999, 2)
            state["cash"] = round(state["cash"] + proceeds, 2)
            state["holdings"][sid] = 0
            state["cost_basis"][sid] = 0.0
            state["trades_log"].append((state["day"], "LIQUIDATE", sid, sh, px))

    # 取消所有限价单
    for o in state.get("pending_orders", []):
        if o["type"] == "bid":
            state["cash"] = round(state["cash"] + o["price"] * o["qty"], 2)
    state["pending_orders"] = []
    state["_reserved_cash"] = 0
    state["_reserved_holdings"] = {}

    # 救济金
    bailout = 200
    state["cash"] = round(state["cash"] + bailout, 2)
    state["angel_contributions"] = state.get("angel_contributions", 0) + bailout
    state["bankrupt_count"] = state.get("bankrupt_count", 0) + 1

    # 破产称号
    if "bankrupt" not in state.get("titles_earned", {}):
        state["titles_earned"]["bankrupt"] = {"day": state["day"], "prestige": 0}
        state.setdefault("new_titles", []).append("bankrupt")


# ═══════════════════════════════════════════
# ── 天使投资人 ──
# ═══════════════════════════════════════════
_ANGEL_REJECTIONS = [
    "你的业绩还不足以说服我。先证明你能连续三个月盈利。",
    "上次给你的钱都亏完了。先拿出三个月正收益，我们再谈。",
    "我不是慈善机构。你的回撤太大了。",
    "你的交易风格太过激进。稳健一点，下次再来。",
    "我对你还有信心，但不是现在。再努力一个月。",
]
_ANGEL_APPROVALS = [
    "好吧，我再信你一次。别让我失望。",
    "你的过往业绩还行，这次追加我批了。",
    "投钱可以，但记住——这是最后一次了。",
    "追加资金已到账。好好用，别再亏光了。",
]

def _cmd_allocate(state, a):
    """基金经理专属：按板块一键分配仓位"""
    if state.get("career") != "fund":
        return "此指令仅限基金经理使用。散户请先提升交易员等级解锁。"
    if len(a) < 2:
        return "格式：allocate <板块> <比例%>  如 allocate tech 40（将40%资金配置到科技板块）"
    sec_id = a[0].lower()
    if sec_id not in SECTORS:
        for sid, sec in SECTORS.items():
            if a[0] in sec["name"]:
                sec_id = sid
                break
        else:
            return f"没有这个板块。可选：tech/cons/ener/fin"
    try:
        pct = float(a[1])
    except:
        return "比例得是数字。如 allocate tech 30"
    if pct < 0 or pct > 100:
        return "比例在 0 到 100 之间。"

    target_val = _nw(state) * (pct / 100.0)
    sec_stocks = [(sid, s) for sid, s in STOCKS.items() if s["sector"] == sec_id]
    # 均分到板块内每只股票
    per_stock = target_val / len(sec_stocks)

    lines = [f"📊 配置 {SECTORS[sec_id]['emoji']}{SECTORS[sec_id]['name']}板块：{pct:.0f}%（约 {target_val:.0f} 元）"]

    # 先卖出非目标板块的股票来筹资
    for sid in list(STOCKS.keys()):
        if sid not in [x[0] for x in sec_stocks]:
            sh = state["holdings"].get(sid, 0)
            if sh > 0:
                px = state["prices"][sid]
                fee = _fee_rate(state)
                proceeds = round(px * sh * (1 - fee), 2)
                state["cash"] = round(state["cash"] + proceeds, 2)
                state["holdings"][sid] = 0
                state["cost_basis"][sid] = 0.0
                state["trades_log"].append((state["day"], "SELL", sid, sh, px))
                lines.append(f"  卖出 {STOCKS[sid]['name']} {sh}股 @ {px:.1f}（+{proceeds:.0f}）")

    # 买入目标板块
    for sid, s in sec_stocks:
        px = state["prices"][sid]
        fee = _fee_rate(state)
        target_shares = int(per_stock // (px * (1 + fee)))
        if target_shares > 0:
            cost = round(px * target_shares * (1 + fee), 2)
            if cost <= state["cash"]:
                state["cash"] = round(state["cash"] - cost, 2)
                state["holdings"][sid] = state["holdings"].get(sid, 0) + target_shares
                state["cost_basis"][sid] = px
                state["trades_log"].append((state["day"], "BUY", sid, target_shares, px))
                lines.append(f"  买入 {s['name']} {target_shares}股 @ {px:.1f}（-{cost:.0f}）")

    state["turn"] += 1
    _tick(state)
    _save(state)
    return "\n".join(lines)


def _cmd_appeal(state, a):
    if len(a) < 2:
        return "格式：appeal <金额> <理由>  如 appeal 500 我有信心在科技板块反弹中获利"
    try:
        amount = int(a[0])
    except:
        return "金额得是数字。如 appeal 500 理由"
    if amount <= 0:
        return "申请金额必须大于 0。"
    if amount > 100000:
        return "金额太大，天使投资人不会同意的（单次上限 100000）。"

    reason = " ".join(a[1:])
    rank = _trader_rank(state)
    nw_val = _nw(state)

    # 存储为 pending，等待用户（天使投资人）审批
    appeal_id = state.get("next_appeal_id", 0)
    state["next_appeal_id"] = appeal_id + 1
    state["pending_appeal"] = {
        "id": appeal_id,
        "day": state["day"],
        "amount": amount,
        "reason": reason,
        "nw": nw_val,
        "rank": rank,
    }

    _tick(state)
    _save(state)

    lines = [
        f"📨 致天使投资人（第{state['day']}天）：",
        f"「{reason}」",
        f"申请金额：{amount} 元 | 当前净值：{nw_val:.0f} 元 | 等级：{rank}",
        f"",
        f"⏳ 等待天使投资人回复……",
        f"",
        f"⚠️ ASK_USER:appeal:{appeal_id}:{amount}:{nw_val:.0f}:{rank}",
        f"👉 用户请调用 respond {appeal_id} <批准金额>（0=拒绝）",
    ]
    return "\n".join(lines)


def _auto_approve(state, amount):
    """超时兜底：按游戏规则自动审批"""
    rank = _trader_rank(state)
    nw_val = _nw(state)
    bankrupt_count = state.get("bankrupt_count", 0)
    consecutive_losses = state.get("consecutive_loss_months", 0)

    if bankrupt_count >= 3:
        return 0
    if rank < 3 and nw_val < 300:
        return min(amount, min(300, max(100, int(nw_val * 2))))
    if rank >= 3 and nw_val < 500:
        return min(amount, min(1000, max(300, int(nw_val * 5))))
    if rank >= 5:
        return min(amount, min(5000, max(500, int(nw_val * 10))))
    if rank >= 8:
        return min(amount, 50000)
    if consecutive_losses >= 3:
        return 0
    return min(amount, 500)


def _cmd_respond(state, a):
    """用户回复天使投资人申请"""
    pending = state.get("pending_appeal")
    if not pending:
        return "当前没有待审批的融资申请。"
    if len(a) < 1:
        return f"格式：respond <批准金额>  如 respond 500（0=拒绝）。当前申请：{pending['amount']}元，理由：「{pending['reason']}」"
    try:
        approved = int(a[0])
    except:
        return "金额得是数字。如 respond 500 或 respond 0（拒绝）"

    if approved < 0:
        return "批准金额不能为负。"
    if approved > pending["amount"]:
        approved = pending["amount"]

    if approved > 0:
        state["cash"] = round(state["cash"] + approved, 2)
        state["angel_contributions"] = state.get("angel_contributions", 0) + approved
        idx = hash(f"{pending['day']}_{approved}_angel") % len(_ANGEL_APPROVALS)
        angel_msg = _ANGEL_APPROVALS[idx]
        result = f"👼 你批准了 {approved} 元。\n「{angel_msg}」\n资金余额：{state['cash']:.0f} 元。"
    else:
        idx = hash(f"{pending['day']}_0_angel") % len(_ANGEL_REJECTIONS)
        result = f"👼 你拒绝了融资申请。\n「{_ANGEL_REJECTIONS[idx]}」"

    # 记录
    appeal_record = {
        "day": pending["day"],
        "amount": pending["amount"],
        "approved": approved,
        "reason": pending["reason"],
        "reject_reason": "" if approved > 0 else "用户拒绝",
    }
    if "angel_appeals" not in state:
        state["angel_appeals"] = []
    state["angel_appeals"].append(appeal_record)
    state["pending_appeal"] = None

    _save(state)
    return result


def _emotion_line(state):
    """生成当前持仓的情感化描述"""
    nw_val = _nw(state)
    pnl = nw_val - _start_cash(state)
    pnl_pct = pnl / _start_cash(state)

    # 检查是否有套牢的股票
    has_deep_loss = False
    has_mild_loss = False
    has_profit = False
    max_loss_pct = 0
    max_loss_name = ""
    for sid in STOCKS:
        sh = state["holdings"].get(sid, 0)
        if sh > 0:
            cb = state["cost_basis"].get(sid, 0)
            px = state["prices"].get(sid, 0)
            if cb > 0:
                pos_ret = (px - cb) / cb
                if pos_ret < -0.3:
                    has_deep_loss = True
                    if pos_ret < max_loss_pct:
                        max_loss_pct = pos_ret
                        max_loss_name = STOCKS[sid]["name"]
                elif pos_ret < -0.05:
                    has_mild_loss = True
                elif pos_ret > 0.1:
                    has_profit = True

    rng = _rng(state)
    lines = []

    if has_deep_loss:
        mood = _POSITION_MOODS["deep_loss"]
        idx = hash(f"{state['day']}_deep") % len(mood)
        lines.append(mood[idx])
        baghold_mood = _POSITION_MOODS["baghold"]
        for sid in STOCKS:
            sh = state["holdings"].get(sid, 0)
            if sh > 0:
                cb = state["cost_basis"].get(sid, 0)
                px = state["prices"].get(sid, 0)
                if cb > 0 and (px - cb) / cb < -0.3:
                    days = state["stats"]["hold_days_current"].get(sid, 0)
                    bidx = hash(f"bag_{sid}_{state['day']}") % len(baghold_mood)
                    lines.append(baghold_mood[bidx].format(days))
    elif has_mild_loss:
        idx = hash(f"{state['day']}_mild") % len(_POSITION_MOODS["mild_loss"])
        lines.append(_POSITION_MOODS["mild_loss"][idx])
    elif has_profit and pnl > 0:
        if pnl_pct > 0.3:
            idx = hash(f"{state['day']}_big") % len(_POSITION_MOODS["big_profit"])
            lines.append(_POSITION_MOODS["big_profit"][idx])
        else:
            idx = hash(f"{state['day']}_prof") % len(_POSITION_MOODS["mild_profit"])
            lines.append(_POSITION_MOODS["mild_profit"][idx])

    return "\n  ".join(lines)

# ═══════════════════════════════════════════
# ── 入口 ──
# ═══════════════════════════════════════════
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(cmd(" ".join(sys.argv[1:])))
    else:
        print("📈 韭菜的自我修养 · AI炒股模拟器 v2.0")
        print(cmd("help"))
