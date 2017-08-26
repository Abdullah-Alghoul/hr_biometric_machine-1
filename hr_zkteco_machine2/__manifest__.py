# -*- coding: utf-8 -*-

{
    'name': 'Biometric Machine2[Zkteco]',
    'version': '1.4.0',
    'author': 'OnGood, OpenPyme',
    'sequence': 0,
    'category': 'Human Resources',
    'website': 'https://www.ongood.cn',
    'license': 'GPL-3',
    'depends': ['hr_attendance'],
    'images': ['static/description/images/main_screenshot.png'],
    'data': [
        'data/zkteco_data.xml',
        'views/zkteco_data_view.xml',
        'views/zkteco_machine_view.xml',
        'views/hr_attendance.xml',
        'views/zkteco_user_view.xml',
        'views/zkteco_user_wizard.xml',
        'views/zkteco_data_wizard.xml',
    ],
    'installable': True,
    'application': True,
    'external_dependencies': {
        # 'python': ['zk',],
    },
}
