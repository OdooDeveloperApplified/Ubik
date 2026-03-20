from odoo.http import request, Response
from odoo import http
import json
from datetime import datetime , timedelta
import secrets
from .token import validate_api_request
import logging
_logger = logging.getLogger(__name__)


class UserController(http.Controller):
    
    @http.route('/user_login', type='http', auth='public', cors='*', methods=['POST'], csrf=False)
    def user_login(self, **kwargs):
        email = kwargs.get('email')
        password = kwargs.get('password')
        device_token = kwargs.get('device_token')
        # credential = {'login': email, 'password': password, 'type': 'password'}


        _logger.info("Login attempt with email: %s", email)

        if not email or not password:
            return Response(json.dumps({
                'success': False,
                'message': 'Email and password are required!',
            }), content_type='application/json')

        #  Search for the user
        user = request.env['res.users'].sudo().search([
            ('login', '=', email),
            ('active', '=', True)
        ], limit=1)
        _logger.info("this is user %s", user)
        if not user:
            inactive_user = request.env['res.users'].sudo().search([
                ('login', '=', email),
                ('active', '=', False)
            ], limit=1)
            if inactive_user:
                _logger.warning("User found but account is deactivated: %s", email)
                return Response(json.dumps({
                    'success': False,
                    'message': 'Account deactivated, please contact support!',
                }), content_type='application/json')
            else:
                return Response(json.dumps({
                    'success': False,
                    'message': 'Email not found!',
                }), content_type='application/json')

        try:
            # ✅ Check password inside try block
            user_env = request.env(user=user)
            credential = {'login': email, 'password': password, 'type': 'password'}
            uid=user_env.user._check_credentials(credential, user_env)
            _logger.info("Password verified successfully for user_id=%s", user.id)


            # 🔎 Find employee linked with this user
            employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
            
            # if not employee.job_id or employee.job_id.name != 'MR':
            #     return Response(json.dumps({
            #         "success": False,
            #         "message": "Only MR users are allowed to generate API token"
            #     }), content_type='application/json')

            allowed_roles = ['MR', 'ASM', 'RSM']

            if not employee.job_id or employee.job_id.name not in allowed_roles:
                return Response(json.dumps({
                    "success": False,
                    "message": "User role not allowed to generate API token"
                }), content_type='application/json')
            
            if user.device_token != device_token:
                _logger.info("Device token changed for user_id=%s. Old: %s, New: %s", 
                           user.id, user.device_token, device_token)
                user.sudo().write({'device_token': device_token})
                _logger.info("Device token updated for user_id=%s", user.id)
            else:
                _logger.info("Device token unchanged for user_id=%s", user.id)

            token = secrets.token_hex(32)
            access_token_dict = {
                'user_id': user.id,
                'api_key': token,
                'expiry_date': datetime.now() + timedelta(days=7)
            }
            create_access_token = request.env['partner.api.key'].sudo().create(access_token_dict)

            # ✅ Build employee details (compact)
            employee_data = {
                'id': employee.id or None,
                'name': employee.name or None,

                # Old code for single territory assigned to MR in Employee module: starts ###############
                # "territory_id": employee.territory_id.id or None,
                # "territory_name": employee.territory_id.name or None,
                # Old code for single territory assigned to MR in Employee module: ends ###############

                # MULTI TERRITORY (FIX) New Code starts here
                "territories": [
                    {
                        "id": t.id,
                        "name": t.name
                    } for t in employee.territory_ids
                ],
                # MULTI TERRITORY (FIX) New Code ends here
                "job_id": employee.job_id.id if employee.job_id else None,
                "job_name": employee.job_id.name if employee.job_id else None,
                'department_id': employee.department_id.id if employee.department_id else None,
                'department': employee.department_id.name if employee.department_id else None,
                'parent_id': employee.parent_id.name if employee.parent_id else None,
                'work_phone': employee.work_phone or None,
                'mobile_phone': employee.mobile_phone or None,
                'work_email': employee.work_email or None,
                # 'parent_users': [{
                #     'id': pu.id,
                #     'name': pu.name,
                #     'email': pu.login
                # } for pu in employee.parent_user_ids] if employee else [],
            }

            # ✅ If no exception, login is successful
            return Response(json.dumps({
                'success': True,
                'message': 'Login Successful!',
                'user_id': user.id,
                'name': user.name,
                'email': user.login,
                'role': employee.job_id.name,
                'employee': employee_data,
                'access_token': create_access_token.api_key,
            }), content_type='application/json')

        except Exception as e:
            # Wrong password or unexpected error
            _logger.warning("Login failed for user %s: %s", email, e)
            return Response(json.dumps({
                'success': False,
                'message': 'Invalid password!',
            }), content_type='application/json')

    @http.route('/user_profile', type='http', auth='public', cors='*', methods=['POST'], csrf=False)
    def get_user_profile(self, **kwargs):

        # :white_tick: Use common helper
        user, error_response = validate_api_request(request, kwargs)
        if error_response:
            return error_response

        # 🔎 User સાથે જોડાયેલ employee
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if not employee:
            return Response(json.dumps({
                "success": False,
                "message": "No employee linked with this user"
            }), content_type='application/json')
        
        # 🔎 Employee નું bank account details
        bank_account = employee.bank_account_id
        branch_address = None
        if bank_account and bank_account.bank_id:
            parts = [
                bank_account.bank_id.street or "",
                bank_account.bank_id.street2 or "",
                bank_account.bank_id.city or "",
                bank_account.bank_id.zip or ""
            ]
            branch_address = ", ".join([p for p in parts if p])

        # 🔎 Prepare private address
        address_parts = []
        if employee.private_street:
            address_parts.append(employee.private_street)
        if employee.private_street2:
            address_parts.append(employee.private_street2)
        if employee.private_city:
            address_parts.append(employee.private_city)
        if employee.private_zip:
            address_parts.append(employee.private_zip)
        if employee.private_state_id:
            address_parts.append(employee.private_state_id.name)
        if employee.private_country_id:
            address_parts.append(employee.private_country_id.name)

        full_address = ", ".join(address_parts) if address_parts else None

        # 🔎 User -> Partner (Contact)
        partner = user.partner_id

        def format_address(p):
            parts = []
            if p.street:
                parts.append(p.street)
            if p.street2:
                parts.append(p.street2)
            if p.city:
                parts.append(p.city)
            if p.zip:
                parts.append(p.zip)
            if p.state_id:
                parts.append(p.state_id.name)
            if p.country_id:
                parts.append(p.country_id.name)
            return ", ".join(parts) if parts else None

        # 🔎 Delivery & Registered (Other) Address
        delivery_address = None
        registered_address = None

        for child in partner.child_ids:
            if child.type == "delivery":
                delivery_address = format_address(child)
            elif child.type == "other":
                registered_address = format_address(child)
        

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

        employee_data = {
            "id": employee.id,
            "user_name": employee.name,
            "name": user.login,
            "job_id": employee.job_id.id if employee.job_id else None,
            "job_name": employee.job_id.name if employee.job_id else None,
            "department_id": employee.department_id.id if employee.department_id else None,
            "department_name": employee.department_id.name if employee.department_id else None,
            "image_url": f"{base_url}/web/image/hr.employee/{employee.id}/image_1920?t={int(datetime.now().timestamp())}",
            "department": employee.department_id.name if employee.department_id else None,
            "private_phone": employee.private_phone or None,
            "mobile_phone": employee.mobile_phone or None,
            "work_phone": employee.work_phone or None,
            "zone": employee.work_location_id.name if employee.work_location_id else None,
            "private_email": employee.private_email or None,
            "work_email": employee.work_email or None,
            "date_of_birth": employee.birthday.strftime("%d-%m-%Y") if employee.birthday else None,
            "gender": employee.gender or None,
            "address": full_address,
            "delivery_address": delivery_address,
            "registered_address": registered_address,
            "account_number": bank_account.acc_number if bank_account else None,
            "bank_name": bank_account.bank_id.name if bank_account and bank_account.bank_id else None,
            "ifsc_code": bank_account.bank_id.bic if bank_account and bank_account.bank_id else None,
            "branch": branch_address,
            "parent_id": employee.parent_id.name if employee.parent_id else None,
        }

        return Response(json.dumps({
            "success": True,
            "employee": employee_data
        }), content_type='application/json')

    @http.route('/delete_account/<int:user_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def deactive_user_account(self, user_id, **kwargs):
        try:
            if user_id:
                user = request.env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
                if user:
                    user.write({'active': False})
                    _logger.info(f"[API] Deactivated user ID {user.id}")
                    data = {
                        'success': True,
                        'message': 'User deactivated successfully!',
                        'user_id': user.id,
                        'login': user.login
                    }
                else:
                    data = {
                        'success': False,
                        'message': 'User not found!',
                    }
            else:
                data = {
                    'success': False,
                    'message': 'Missing user_id!',
                }
        except Exception as e:
            _logger.exception("Error during user deactivation")
            data = {
                'success': False,
                'message': f'Exception: {str(e)}'
            }
        return http.Response(json.dumps(data), content_type='application/json')

    @http.route('/settings', type='http', auth='public', methods=['GET'], csrf=False)
    def get_app_versions(self, **kwargs):
        try:
            # :white_tick: Single record fetch (since only one allowed)
            app_version = request.env['app.version'].sudo().search([], limit=1)
            if not app_version:
                return Response(json.dumps({
                    "status": "error",
                    "message": "No app version found"
                }), content_type="application/json", status=200)
            data = {
                "android_version": app_version.android_version,
                "ios_version": app_version.ios_version,
            }
            return Response(json.dumps({
                "status": "success",
                "data": data
            }, default=str), content_type="application/json", status=200)
        except Exception as e:
            return Response(json.dumps({
                "status": "error",
                "message": str(e)
            }), content_type="application/json", status=200)