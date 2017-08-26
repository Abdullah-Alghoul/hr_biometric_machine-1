# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from mock import patch
from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.translate import _

import datetime
import itertools
import pytz
import sys
# 解决中控考勤机导出中文姓名乱码问题
reload(sys)
sys.setdefaultencoding('gbk')
# 链接到本地库pyzk
from odoo.addons.hr_zkteco_machine2.pyzk.zk.attendance import Attendance
from odoo.addons.hr_zkteco_machine2.pyzk.zk import ZK


class ZktecoMachine(models.Model):
    _name = 'biometric.machine'

    @property
    def min_time(self):
        # Get min time
        if self.interval_min == 'sec':
            min_time = datetime.timedelta(seconds=self.time_interval_min)
        elif self.interval_min == 'min':
            min_time = datetime.timedelta(minutes=self.time_interval_min)
        elif self.interval_min == 'hour':
            min_time = datetime.timedelta(hours=self.time_interval_min)
        else:
            min_time = datetime.timedelta(days=self.time_interval_min)
        return min_time

    @property
    def max_time(self):
        # Get min time
        if self.interval_max == 'sec':
            max_time = datetime.timedelta(seconds=self.time_interval_max)
        elif self.interval_max == 'min':
            max_time = datetime.timedelta(minutes=self.time_interval_max)
        elif self.interval_max == 'hour':
            max_time = datetime.timedelta(hours=self.time_interval_max)
        else:
            max_time = datetime.timedelta(days=self.time_interval_max)
        return max_time

    @api.model
    def _tz_get(self):
        # Copied from base model
        return [
            (tz, tz) for tz in
            sorted(
                pytz.all_timezones,
                key=lambda tz: tz if not
                tz.startswith('Etc/') else '_')]

    name = fields.Char('Name')
    ip_address = fields.Char('Ip address')
    port = fields.Integer('Port')
    sequence = fields.Integer('Sequence')
    timezone = fields.Selection(
        _tz_get, 'Timezone', size=64,
        help='Divice timezone',
    )
    time_interval_min = fields.Integer(
        'Min time',
        help='Min allowed time  between two registers')
    interval_min = fields.Selection(
        [('sec', 'Sec(s)'), ('min', 'Min(s)'),
         ('hour', 'Hour(s)'), ('days', 'Day(s)'), ],
        'Min allowed time', help='Min allowed time between two registers',)
    time_interval_max = fields.Integer(
        'Max time',
        help='Max allowed time  between two registers',)
    interval_max = fields.Selection(
        [('sec', 'Sec(s)'), ('min', 'Min(s)'),
         ('hour', 'Hour(s)'), ('days', 'Day(s)'), ],
        'Max allowed time', help='Max allowed time between two registers',)

    @api.model
    def get_users(self):
        """
        Function use to get all the registered users
        at the biometric device
        """
        with ConnectToDevice(self.ip_address, self.port) as conn:
            users = conn.get_users()
        return users

    @api.model
    def clean_attendance(self):
        """
        Function use to clean all attendances
        at the biometric device
        """
        with ConnectToDevice(self.ip_address, self.port) as conn:
            conn.clear_attendance()

    @api.model
    def create_user(self):
        """
        function uses to assure that all users are alredy
        created in odoo
        """
        biometric_user_obj = self.env['biometric.user']
        users = self.get_users()
        odoo_users = biometric_user_obj.search([
            ('biometric_device', '=', self.id), ], )
        odoo_users_id = [user.biometric_id for user in odoo_users]
        for user in users:
            if int(user.user_id) not in odoo_users_id:
                biometric_user_obj.create({
                     'biometric_id': int(user.user_id),
                     'name': user.name,
                     'biometric_device': self.id, }
                )
                

    # @patch('zk.base.Attendance',OdooAttendance)
    def getattendance(self):
        """
        Function uses to get attendances
        """
        self.create_user()
        with ConnectToDevice(self.ip_address, self.port) as conn:
            attendaces = conn.get_attendance()
        # Attendances are group by user
        for user_attendances in attendaces:
            # Compare each user attendance to review 
            # if fulfill minimun time condition
            for a, b in itertools.combinations(user_attendances, 2):
                if a.action_perform != b.action_perform:
                    continue
                if abs(a.timestamp - b.timestamp) < self.min_time:
                    user_attendances.remove(a)
        return attendaces


class ConnectToDevice(object):
    """
    Class uses to assure connetion to a device and closing of the same
    It is using to disable the device when it is been reading or busy
    """

    def __init__(self, ip_address, port):
        try:
            zk = ZkOdoo(ip_address, port)
            conn = zk.connect()
        except:
            raise UserError(
                _('Unexpected error: {error}'.format(error=sys.exc_info()),)
            )
        conn.disable_device()
        self.conn = conn

    def __enter__(self):
        """
        return biometric connection
        """
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        enable device and close connection
        """
        self.conn.enable_device  # noqa: W0104
        self.conn.disconnect()
        
        

class ZktecoData(models.Model):
    _name = 'biometric.data'

    # Order records by date to assure will be crated
    # first the oldest registers
    _order = 'datetime'

    @api.multi
    def _compute_get_employee_id(self):
        if self.biometric_user_id.employee_id:
            self.employee_id = self.biometric_user_id.employee_id

    @api.multi
    def _compute_get_name(self):
        if self.biometric_user_id:
            self.name = self.biometric_user_id.name

    datetime = fields.Datetime('Date')
    biometric_user_id = fields.Many2one(
        'biometric.user', 'Related biometric user',)
    employee_id = fields.Many2one(
        'hr.employee', 'Related employee', compute=_compute_get_employee_id,)
    name = fields.Char(
        'Employee name in biometric device',
        compute=_compute_get_name,)
    action_perform = fields.Char('Action perform')

    @api.model
    def create_hr_attendace(
            self, employee_id, date, action_perform,
            biometric_id, state='right',):
        """
        Register have to be always: check_in, check_out, check_in and so on
        In hr_attedance moules there is a a contrain
        which assures never a check_in or a check_out are next to the same kind
        of regiter, this means register are followed are wrong
            check_out, check_in, check_in  --> because there are next to two check_in
            check_out, check_out, check_in  --> because there are next to two check_out
        User could forget to sign incoming and outcoming regiters a lot of times
        This function assures that regardless contrain continue being true
        """
        hr_attendance_obj = self.env['hr.attendance']
        biometric_machine_obj = self.env['biometric.machine']
        biometric_machine = biometric_machine_obj.browse(biometric_id)

        def convert_date_to_utc(date):
            local = pytz.timezone(
                biometric_machine.timezone,)
            date = local.localize(date, is_dst=None)
            date = date.astimezone(pytz.utc)
            date.strftime('%Y-%m-%d: %H:%M:%S')
            return date.replace(tzinfo=None)

        def convert_from_local_to_utc(date):
            local = pytz.timezone(
                biometric_machine.timezone,)
            date = date.replace(tzinfo=pytz.utc)
            date = date.astimezone(local)
            date.strftime('%Y-%m-%d: %H:%M:%S')
            return date.replace(tzinfo=None)

        # Get the max time of working set up for the device
        max_time = biometric_machine.max_time
        # Get a delta time of 1 minute
        delta_1_minute = datetime.timedelta(minutes=1)
        # Get previous attendace
        prev_att = hr_attendance_obj.search(
            [('employee_id', '=', employee_id),
             ('name', '<', convert_date_to_utc(date).isoformat()),
             ('action', 'in', ('check_in', 'check_out'),), ],
            limit=1, order='name DESC',)
        # Get date of the last user register
        if not prev_att:
            employee_date = date
        else:
            employee_date = datetime.datetime.strptime(
                prev_att.name, '%Y-%m-%d %H:%M:%S',)
        employee_date = convert_from_local_to_utc(employee_date)
        if action_perform == 'check_in':
            if prev_att and prev_att.action == action_perform:
                if abs(employee_date - date) >= max_time:
                    new_time = employee_date + max_time
                    self.create_hr_attendace(
                        employee_id, new_time, 'check_out',
                        biometric_id, state='fix',)
                else:
                    new_time = date - delta_1_minute
                    self.create_hr_attendace(
                        employee_id, new_time, 'check_out',
                        biometric_id, state='fix',)
        else:
            if (not prev_att or prev_att.action == action_perform or
                    abs(employee_date - date) > max_time):
                new_time = date - delta_1_minute
                self.create_hr_attendace(
                    employee_id, new_time, 'check_in',
                    biometric_id, state='fix',)
        # Convert date using correct timezone
        date = convert_date_to_utc(date)
        self._create_hr_attendace(employee_id, date, action_perform, state)

    @api.model
    def _create_hr_attendace(
            self, employee_id, date, action_perform, state,):
        hr_attendance_obj = self.env['hr.attendance']
        hr_attendance_obj.create(
            {'employee_id': employee_id,
             'name': date.strftime('%Y-%m-%d: %H:%M:%S'),
             'action': action_perform,
             'state': state, }
        )

    @classmethod
    def convert_to_hr_attendance_classmethod(
            cls, biometric_data, biometric_data_obj,):
        for datum in biometric_data:
            if not datum.employee_id:
                continue
            date = datetime.datetime.strptime(
                datum.datetime, '%Y-%m-%d %H:%M:%S',)
            biometric_data_obj.create_hr_attendace(
                datum.employee_id.id, date,
                datum.action_perform,
                datum.biometric_user_id.biometric_device.id,
            )
            datum.unlink()

    @classmethod
    def import_data_classmethod(
            cls, biometric_machine, biometric_data_obj, biometric_user_obj,):
        attendances = biometric_machine.getattendance()
        for user_attendances in attendances:
            # Sorted elements using timestamp
            user_attendances.sort(key=lambda x: x.timestamp)
            user = biometric_user_obj.search([
                    ['biometric_id', '=', int(
                        user_attendances[0].user_id), ], ], )
            for attendance in user_attendances:
                if not attendance.action_perform:
                    continue
                elif not user.employee_id:
                    biometric_data_obj.create(
                        {'biometric_user_id': user.id,
                         'datetime': attendance.timestamp,
                         'action_perform': attendance.action_perform, }, )
                else:
                    biometric_data_obj.create_hr_attendace(
                        user.employee_id.id, attendance.timestamp,
                        attendance.action_perform,
                        user.biometric_device.id,)
        biometric_machine.clean_attendance()

    @api.model
    def convert_to_hr_attendance(self):
        biometric_data = self.search([])
        self.convert_to_hr_attendance_classmethod(
            biometric_data, self,)

    @api.model
    def import_data(self):
        biometric_machine_obj = self.env['biometric.machine']
        biometric_user_obj = self.env['biometric.user']
        # First of all convert the oldest registers
        # into hr.attendance registers
        self.convert_to_hr_attendance()
        biometric_machines = biometric_machine_obj.search([])
        for biometric_machine in biometric_machines:
            self.import_data_classmethod(
                biometric_machine, self, biometric_user_obj,)
                
class BiometricDataWizard(models.TransientModel):
    _name = 'biometric.data.wizard'

    biometric_device = fields.Many2one(
        'biometric.machine', 'Biometric device',
    )

    def import_attendance(self):
        """
        wrapper function
        """
        for biometric_attendance in self:
            biometric_attendance.crate_attendance_in_odoo()

    @api.model
    def crate_attendance_in_odoo(self):
        """
        Call import function in biometric.data model
        """
        biometric_data_obj = self.env['biometric.data']
        biometric_user_obj = self.env['biometric.user']
        biometric_data_bio = biometric_data_obj.search([])
        BiometricData.convert_to_hr_attendance_classmethod(biometric_data_bio, biometric_data_obj,)
        biometric_machine = self.biometric_device
        BiometricData.import_data_classmethod(biometric_machine, biometric_data_obj, biometric_user_obj,)
            
class BiometricUser(models.Model):
    _name = 'biometric.user'

    biometric_id = fields.Integer('Id in biometric device')
    name = fields.Char('Name in biometric device')
    employee_id = fields.Many2one('hr.employee', 'Related employee')
    biometric_device = fields.Many2one(
        'biometric.machine', 'Biometric device',
    )

    _sql_constraints = [
        ('employee_id_uniq', 'unique (employee_id)',
         'It is not possible relate an employee with a biometric user '
         'more than once!'),
    ]

    _sql_constraints = [
        ('biometric_id_uniq', 'unique (biometric_id)',
         'It is not possible to crate more than one '
         'with the same biometric_id'),
    ]

class BiometricUser(models.TransientModel):
    _name = 'biometric.user.wizard'

    biometric_device = fields.Many2one(
        'biometric.machine', 'Biometric device',
    )

    def import_users(self):
        """
        wrapper function
        """
        for biometric_import_user in self:
            biometric_import_user.create_users_in_odoo()
  
    @api.model
    def create_users_in_odoo(self):
        self.biometric_device.create_user()
        
class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    
    @api.one
    def fix_register(self):
        self.write({'state': 'right'})

    state = fields.Selection(
        selection=[('fix', 'Fix'), ('right', 'Right')],
        default='right',
        help='The user did not register an input '
        'or an output in the correct order, '
        'then the system proposed one or more regiters to fix the problem '
        'but you must review the created register due '
        'becouse of hour could be not correct' )
        
class ZkOdoo(ZK):

    def get_attendance(self):
        attendances = super(ZkOdoo, self).get_attendance()
        # Group by users
        attendaces_odoo = []
        uniquekeys = []
        attendances = sorted(attendances, key=lambda x: x.user_id)
        for k, g in groupby(attendances, lambda x: x.user_id):
            attendaces_odoo.append(list(g))
            uniquekeys.append(k)
        return attendaces_odoo


class OdooAttendance(Attendance):

    @property
    def action_perform(self):
        actions = {
            0: 'check_in',
            1: 'check_out',
        }
        return actions.get(self.status)
