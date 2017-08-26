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
        'data/biometric_data.xml',
        'views/biometric_data_view.xml',
        'views/biometric_machine_view.xml',
        'views/hr_attendance.xml',
        'views/biometric_user_view.xml',
        'views/biometric_user_wizard.xml',
        'views/biometric_data_wizard.xml',
    ],
    'installable': True,
    'application': True,
    'external_dependencies': {
        # 'python': ['zk',],
    },
}
