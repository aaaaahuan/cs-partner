# CS2 Grenade Lineups Database

# 投掷方式常量
THROW_JUMP = "跳投 (Jump Throw)"
THROW_NORMAL = "普通投掷 (Normal Throw)"
THROW_RUN_JUMP = "跑动跳投 (Run Jump Throw)"
THROW_RIGHT_CLICK = "右键投掷 (Right Click)"

# 道具类型常量
TYPE_SMOKE = "Smoke (烟雾弹)"
TYPE_FLASH = "Flash (闪光弹)"
TYPE_MOLY = "Molotov (燃烧瓶)"

GRENADE_DATA = {
    "Mirage": [
        {
            "name": "CT Spawn Smoke from T Spawn",
            "type": TYPE_SMOKE,
            "desc": "封锁警家视野，用于进攻 A 点",
            "stance": "T 家出生点右侧栅栏角落",
            "aim": "瞄准 A 点上方天线右侧突出点",
            "throw": THROW_JUMP
        },
        {
            "name": "Stairs Smoke from T Roof",
            "type": TYPE_SMOKE,
            "desc": "封锁楼梯视野",
            "stance": "T 家高台侧面墙壁",
            "aim": "瞄准木板中间",
            "throw": THROW_NORMAL
        },
        {
            "name": "Jungle Smoke from T Roof",
            "type": TYPE_SMOKE,
            "desc": "封锁连接和狙击位视野",
            "stance": "T 家高台最左侧柱子旁",
            "aim": "瞄准天空中云层缺口",
            "throw": THROW_NORMAL
        },
        {
            "name": "Mid Window Smoke from T Spawn",
            "type": TYPE_SMOKE,
            "desc": "中路 VIP 烟雾弹 (瞬爆)",
            "stance": "T 家垃圾桶旁蹲下",
            "aim": "瞄准门框右上角",
            "throw": THROW_run_JUMP
        }
    ],
    "Inferno": [
        {
            "name": "Coffin Smoke from Banana",
            "type": TYPE_SMOKE,
            "desc": "封锁棺材视野",
            "stance": "香蕉道木堆旁",
            "aim": "瞄准电线杆顶端",
            "throw": THROW_NORMAL
        },
        {
            "name": "CT Smoke from Banana",
            "type": TYPE_SMOKE,
            "desc": "封锁 CT 通道视野",
            "stance": "香蕉道原木堆后",
            "aim": "瞄准屋檐尖角",
            "throw": THROW_NORMAL
        }
    ],
    "Dust2": [
        {
            "name": "Xbox Smoke from T Spawn",
            "type": TYPE_SMOKE,
            "desc": "中路 Xbox 烟雾弹",
            "stance": "T 家出生点",
            "aim": "瞄准墙上黑点",
            "throw": THROW_JUMP
        },
        {
            "name": "Long A Corner Smoke",
            "type": TYPE_SMOKE,
            "desc": "A 大过点烟",
            "stance": "A 门外箱子后",
            "aim": "瞄准路灯顶部",
            "throw": THROW_NORMAL
        }
    ]
}

def get_maps():
    return list(GRENADE_DATA.keys())

def get_grenades(map_name):
    return GRENADE_DATA.get(map_name, [])
