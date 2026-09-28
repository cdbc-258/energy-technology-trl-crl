"""Q/GDW stage requirements; CRL operational rules remain a project draft."""
VERSION = 'QGDW-evidence-v3.0'
TRL = {
    1: {'principle': '明确基本原理及其与目标技术的关联'},
    2: {'application': '具体应用设想、对象、场景及基本功能'},
    3: {'design': '确定技术路线并完成方案设计', 'theory': '完成关键功能的理论可行性验证'},
    4: {'critical': '系统关键技术/模型及被验证功能明确',
        'laboratory': '已在实验室或离线模型环境开展对应验证',
        'validation': '有对应功能的已完成验证结果及适用边界'},
    5: {'component': '关键部件/分系统或软件子模块已形成',
        'integration': '部件与试验装置集成；软件可为可执行子模块',
        'environment': '模拟使用环境及其与目标使用条件的关系有依据',
        'qualification': '测试数据证实达到已定义的相关要求'},
    6: {'prototype': '可识别的原型及目标功能、形态/尺度边界',
        'integration': '关键部件组成所评原型；软件为系统级原型',
        'environment': '原型测试环境覆盖本阶段关键使用条件',
        'qualification': '对应关键功能和性能要求已有测试与达成证据'},
    7: {'engineering': '明确工程型号/工程测试版本',
        'typical': '典型使用环境覆盖最终环境的关键要素',
        'type_test': '设备完成型式试验；软件完成典型数据下工程测试及运行数据对照',
        'qualification': '参数与性能达到专属细则要求'},
    8: {'product': '系统级产品或正式软件版本',
        'online': '已挂网/上线试运行',
        'comprehensive': '对应测试清单已全面完成并处置问题'},
    9: {'product': '可识别工程产品或有界产品族',
        'application': '实际工程成功使用并有功能性能证据',
        'scale': '具备规模推广条件或已有批量交付应用',
        'typical': '实际应用与目标用途、环境一致'},
}
CRL = {
    1: {'absence': '在限定对象、期间和商业活动范围内有直接无商业化证明'},
    2: {'users': '具体目标用户及需求', 'trial': '已开展用户试用/需求或商业模式验证',
        'value': '形成用户价值或商业探索反馈'},
    3: {'parties': '可识别供需主体', 'fulfilment': '已发生销售/供货/许可/结算等履约',
        'period': '履约时间范围和结果明确'},
    4: {'repeat': '持续或重复商业交付', 'capacity': '供应/交付/运维能力',
        'economics': '持续商业经济性有可核实依据'},
    5: {'market': '细分市场、期间及份额分母明确', 'dominance': '市场成熟及主导性有依据',
        'durability': '持续经营与竞争能力有依据'},
}
NAMES = {
    'TRL': ['基本原理', '应用设想', '理论可行性验证', '实验环境验证', '部件功能测试',
            '原型验证', '工程测试', '产品试运行', '产品应用'],
    'CRL': ['无商业化活动', '市场探索', '早期市场进入', '规模化商业应用', '市场成熟与主导地位'],
}


def requirements(axis, level):
    if axis not in {'TRL', 'CRL'} or type(level) is not int:
        raise ValueError('invalid axis or non-integer level')
    rules = TRL if axis == 'TRL' else CRL
    if level not in rules:
        raise ValueError('level outside scale')
    return rules[level]
