from odoo import http,fields
from odoo.http import request, Response
from .token import validate_api_request
from datetime import datetime
import json
import logging

_logger = logging.getLogger(__name__)

############### API to list product categories present in odoo databse in mobile app ##########################

class ProductCategoryAPI(http.Controller):

    @http.route('/product_category', type='http', auth='public', cors='*', methods=['POST'], csrf=False)

    def get_category_types(self, **kwargs):
            # Common helper function for user validation
            user, error_response = validate_api_request(request, kwargs)
            if error_response:
                return error_response

            categories = request.env['product.category'].sudo().search([])

            if not categories:
                return Response(
                    json.dumps({
                        "success": False,
                        "message": "No product categories found"
                    }),
                    content_type='application/json'
                )

            data = [{'id': c.id,'name': c.name} for c in categories]

            return Response(
                json.dumps({
                    'success': True,
                    'count': len(data),
                    'categories': data
                }),
                status=200,
                content_type='application/json'
            )

############### API to list product as per the category(division) choosen ##########################

class ProductAPI(http.Controller):

    @http.route('/products_by_category', type='http', auth='public', cors='*', methods=['POST'], csrf=False)

    def get_products_by_category(self, **kwargs):

        user, error_response = validate_api_request(request, kwargs)
        if error_response:
            return error_response

        category_id = kwargs.get('category_id')
        territory_id = kwargs.get('territory_id')
        if not category_id:
            return Response(
                json.dumps({
                    "success": False,
                    "message": "category_id is required"
                }),
                status=400,
                content_type='application/json'
            )
        if not territory_id:
            return Response(
                json.dumps({
                    "success": False,
                    "message": "territory_id is required for product filtering"
                }),
                status=400,
                content_type='application/json'
            )
        
        # Validate that the territory belongs to the MR
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id)
        ], limit=1)

        if not employee:
            return Response(json.dumps({
                "success": False,
                "message": "Employee (MR) not found"
            }), content_type='application/json')

        if int(territory_id) not in employee.territory_ids.ids:
            return Response(json.dumps({
                "success": False,
                "message": "Territory not assigned to this MR"
            }), content_type='application/json')
        
        category = request.env['product.category'].sudo().browse(int(category_id))
        if not category.exists():
            return Response(
                json.dumps({
                    "success": False,
                    "message": "Invalid category_id"
                }),
                content_type='application/json'
            )

        all_products = request.env['product.template'].sudo().search([
            ('categ_id', 'child_of', int(category_id)),
            ('active', '=', True),
           
        ])

        # Filter products based on territory
        filtered_products = request.env['product.template']
        
        for product in all_products:
            
            if product.is_territory_specific_product:
                if int(territory_id) in product.allowed_territory_ids.ids:
                    filtered_products |= product
            else:
                # If product is not territory specific, include it
                filtered_products |= product

        if not filtered_products:
            return Response(
                json.dumps({
                    "success": False,
                    "message": "No products found for this category in the selected territory"
                }),
                content_type='application/json'
            )
            
        data = [{
            'id': p.id,
            'name': p.name,
            'price': p.list_price,
            'category_id': p.categ_id.id,
            'is_territory_specific': p.is_territory_specific_product,
            'allowed_territories': [t.id for t in p.allowed_territory_ids] if p.is_territory_specific_product else []  
        } for p in filtered_products]

        return Response(
            json.dumps({
                'success': True,
                'count': len(data),
                'products': data
            }),
            status=200,
            content_type='application/json'
        )

############### API to list product category as per the categories assigned to MR ##########################

class MRCategoryAPI(http.Controller):

    @http.route('/mr_product_categories', type='http', auth='public', cors='*', methods=['POST'], csrf=False)

    def get_mr_categories(self, **kwargs):

        user, error_response = validate_api_request(request, kwargs)
        if error_response:
            return error_response

        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id)
        ], limit=1)

        if not employee:
            return Response(json.dumps({
                "success": False,
                "message": "Employee (MR) not found"
            }), content_type='application/json')

        categories = employee.product_category_ids
        if not categories:
            return Response(
                json.dumps({
                    "success": False,
                    "message": "No product categories assigned to this MR"
                }),
                content_type='application/json'
            )
        
        data = [{
            "id": c.id,
            "name": c.name
        } for c in categories]

        return Response(json.dumps({
            "success": True,
            "count": len(data),
            "categories": data
        }), content_type='application/json')
    
############### NEW CODE : API to list territories assigned to MR ##########################  
class MRTerritoryAPI(http.Controller):

    @http.route('/mr_territories', type='http', auth='public', cors='*', methods=['POST'], csrf=False)

    def get_mr_territories(self, **kwargs):

        user, error_response = validate_api_request(request, kwargs)
        if error_response:
            return error_response

        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', user.id)], limit=1)

        if not employee or not employee.territory_ids:
            return Response(json.dumps({
                "success": False,
                "message": "No territories assigned"
            }), content_type='application/json')

        data = [{'id': t.id, 'name': t.name}
                for t in employee.territory_ids]

        return Response(json.dumps({
            "success": True,
            "count": len(data),
            "territories": data
        }), content_type='application/json')

class MRDoctorAPI(http.Controller):

    @http.route('/doctor_list_by_territory', type='http', auth='public', cors='*', methods=['POST'], csrf=False)

    def get_doctors_by_territory(self, **kwargs):

        user, error_response = validate_api_request(request, kwargs)
        if error_response:
            return error_response

        territory_id = kwargs.get('territory_id')
        if not territory_id:
            return Response(json.dumps({
                "success": False,
                "message": "territory_id is required"
            }), content_type='application/json')

        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', user.id)], limit=1)

        if int(territory_id) not in employee.territory_ids.ids:
            return Response(json.dumps({
                "success": False,
                "message": "Territory not assigned to MR"
            }), content_type='application/json')

        doctors = request.env['res.partner'].sudo().search([
            ('is_doctor', '=', True),
            ('territory_id', '=', int(territory_id)),
            ('active', '=', True)
        ])

        data = [{
            'id': d.id,
            'name': d.name,
            'territory_id': d.territory_id.id
        } for d in doctors]

        return Response(json.dumps({
            "success": True,
            "count": len(data),
            "doctors": data
        }), content_type='application/json')

############### API to manage Rate type ########################## 

class MRRateAPI(http.Controller):

    @http.route('/get_rate_type', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_rate_by_type(self, **kwargs):

        user, error_response = validate_api_request(request, kwargs)
        if error_response:
            return error_response

        product_id = kwargs.get('product_id')
        rate_type = kwargs.get('rate_type')

        # Convert quantity safely
        try:
            quantity = float(kwargs.get('quantity', 1))
        except (TypeError, ValueError):
            return Response(json.dumps({
                "success": False,
                "message": "Invalid quantity value"
            }), content_type='application/json')

        # Convert custom_price safely
        try:
            custom_price = float(kwargs.get('custom_price', 0))
        except (TypeError, ValueError):
            return Response(json.dumps({
                "success": False,
                "message": "Invalid custom_price value"
            }), content_type='application/json')

        if not product_id or not rate_type:
            return Response(json.dumps({
                "success": False,
                "message": "product_id and rate_type are required"
            }), content_type='application/json')

        if quantity <= 0:
            return Response(json.dumps({
                "success": False,
                "message": "Quantity must be greater than zero"
            }), content_type='application/json')

        product = request.env['product.template'].sudo().browse(int(product_id))
        if not product.exists():
            return Response(json.dumps({
                "success": False,
                "message": "Invalid product"
            }), content_type='application/json')

        if rate_type == 'ptr_rate':
            unit_price = product.list_price

        elif rate_type == 'custom_rate':

            if custom_price <= 0:
                return Response(json.dumps({
                    "success": False,
                    "message": "Custom price must be greater than zero"
                }), content_type='application/json')

            if custom_price > product.list_price:
                return Response(json.dumps({
                    "success": False,
                    "message": "Custom price cannot exceed PTR rate"
                }), content_type='application/json')

            unit_price = custom_price

        else:
            return Response(json.dumps({
                "success": False,
                "message": "Invalid rate type"
            }), content_type='application/json')

        amount = unit_price * quantity

        return Response(json.dumps({
            "success": True,
            "data": {
                "product_id": product.id,
                "rate_type": rate_type,
                "unit_price": unit_price,
                "quantity": quantity,
                "amount": amount
            }
        }), content_type='application/json')

class MrDoctorCreateAPI(http.Controller):

    @http.route('/create_mr_doctor_visit_record', type='http', auth='public', cors='*', methods=['POST'], csrf=False)

    def create_mr_doctor(self, **kwargs):

        user, error_response = validate_api_request(request, kwargs)
        if error_response:
            return error_response
        
        user_id = kwargs.get('user_id')
        mr_id = kwargs.get('mr_id') or user_id
        territory_id = kwargs.get('territory_id')
        doctor_id = kwargs.get('doctor_id')

        if not territory_id or not doctor_id:
            return Response(json.dumps({
                "success": False,
                "message": "territory_id and doctor_id are required"
            }), content_type='application/json')

        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', user.id)], limit=1)
        
        if not employee:
            return Response(json.dumps({
                "success": False,
                "message": "Employee not linked to this user"
            }), content_type='application/json')

        if not user.has_group('ubik_app.group_sales_user'):
            return Response(json.dumps({
                "success": False,
                "message": "You are not allowed to create visit records"
            }), content_type='application/json')

        # Allow MR / ASM / RSM only
        if employee.job_id.name not in ['MR', 'ASM', 'RSM']:
            return Response(json.dumps({
                "success": False,
                "message": "Only MR, ASM or RSM can create visit records"
            }), content_type='application/json')

        if int(territory_id) not in employee.territory_ids.ids:
            return Response(json.dumps({
                "success": False,
                "message": "Territory not assigned to MR"
            }), content_type='application/json')

        doctor = request.env['res.partner'].sudo().browse(int(doctor_id))
        if not doctor.is_doctor:
            return Response(json.dumps({
                "success": False,
                "message": "Invalid doctor"
            }), content_type='application/json')
        
        # CHECK IF THIS IS FIRST RECORD TODAY BEFORE CREATING
        today = fields.Datetime.now()
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        existing_today_count = request.env['mr.doctor'].sudo().search_count([
            ('mr_id', '=', user.id),
            ('create_date', '>=', start_of_day),
            ('create_date', '<=', end_of_day)
        ])
        
        is_first_today = 1 if existing_today_count == 0 else 0

        mr_doctor = request.env['mr.doctor'].sudo().create({
            'mr_id': user.id,
            'territory_id': int(territory_id),
            'doctor_id': doctor.id,
            'doc_unique_id': doctor.doc_unique_id,
        })

        # Create Lines
        order_lines = []
        index = 0
        created_lines = 0

        while True:
            category_id = kwargs.get(f'line_category_id[{index}]')
            product_id = kwargs.get(f'line_product_id[{index}]')

            if not category_id or not product_id:
                break

            month = kwargs.get(f'line_month[{index}]') or datetime.today().strftime('%Y-%m')

            rate_type = kwargs.get(f'line_rate_type[{index}]')
            qty = float(kwargs.get(f'line_qty[{index}]', 1))
            price = float(kwargs.get(f'line_price[{index}]', 0))

            product = request.env['product.template'].sudo().browse(int(product_id))
            if not product.exists():
                return Response(json.dumps({
                    "success": False,
                    "message": f"Invalid product_id: {product_id}"
                }), content_type='application/json')
            
            if product.is_territory_specific_product:
                if int(territory_id) not in product.allowed_territory_ids.ids:
                    return Response(json.dumps({
                        "success": False,
                        "message": f"Product '{product.display_name}' is not allowed in the selected territory"
                    }), content_type='application/json')
            
            if rate_type not in ['ptr_rate', 'custom_rate']:
                return Response(json.dumps({
                    "success": False,
                    "message": f"Invalid rate type at line {index}"
                }), content_type='application/json')

            # PTR logic
            if rate_type == 'ptr_rate':
                price = product.list_price
            
            if rate_type == 'custom_rate' and price > product.list_price:
                return Response(json.dumps({
                    "success": False,
                    "message": f"Custom price cannot exceed PTR rate for product {product.display_name}"
                }), content_type='application/json')

            # Check for duplicate entry BEFORE creating
            existing_entry = request.env['mr.doctor.line'].sudo().search([
                ('mr_doctor_id.doctor_id', '=', int(doctor_id)),
                ('product_id', '=', int(product_id)),
                ('month', '=', month),
                ('mr_doctor_id.mr_id', '=', user.id),  # Ensure it's the same MR
                ('mr_doctor_id', '!=', mr_doctor.id)
            ], limit=1)

            if existing_entry:
                # Duplicate found - rollback the header if this is the first line
                if index == 0:  # If this is the first line and duplicate, delete the header
                    mr_doctor.sudo().unlink()
                
                return Response(json.dumps({
                    "success": False,
                    "message": f"Duplicate entry: Product '{product.display_name}' for Dr. {doctor.name} in month {month} already exists. Duplicate records are not allowed."
                }), content_type='application/json')

            order_lines.append({
                'mr_doctor_id': mr_doctor.id,
                'category_id': int(category_id),
                'product_id': product.id,
                'rate_type': rate_type,
                'price_unit': price,
                'product_qty': qty,
                'month': month,
              
            })

            created_lines += 1
            index += 1

        if not order_lines:
            return Response(json.dumps({
                "success": False,
                "message": "At least one product is required"
            }), content_type='application/json')

        request.env['mr.doctor.line'].sudo().create(order_lines)

        # Automatically submit to manager
        mr_doctor = mr_doctor.with_user(user)
        mr_doctor.action_submit_to_asm()

        return Response(json.dumps({
            "success": True,
            "message": "MR Doctor visit created and submitted to manager",
            "mr_doctor_id": mr_doctor.id,
            "reference": mr_doctor.name,
            "status": mr_doctor.asm_state,
            "is_first_today": is_first_today,  # Add this to response
            "declaration_required": is_first_today  # Add this for app to know if declaration needed
        }), content_type='application/json')


class MRDoctorListAPI(http.Controller):

    @http.route('/list_mr_doctor_visits', type='http', auth='public', cors='*', methods=['POST'], csrf=False)
    def list_mr_doctor_visits(self, **kwargs):
        """
        List MR doctor visits along with edit/delete permissions
        (integrates logic from /check_mr_doctor_edit_permission API)
        """

        try:
            # Validate token & user
            user, error_response = validate_api_request(request, kwargs)
            if error_response:
                return error_response

            mr_visits = request.env['mr.doctor'].sudo().search([
                ('mr_id', '=', user.id)
            ], order='create_date desc')

            if not mr_visits:
                return Response(json.dumps({
                    "success": False,
                    "message": "No MR doctor visits found"
                }), content_type='application/json')

            current_month = datetime.today().strftime('%Y-%m')

            visits_data = []

            for visit in mr_visits:

                line_items = []

                # ===== IMPROVED PERMISSION LOGIC =====
                # Check if any line is from current month
                is_current_month = any(
                    line.month == current_month for line in visit.line_ids
                )

                # Check if record is locked (past month and not unlocked by admin)
                # record_save is True for past month records that are NOT unlocked
                is_locked = visit.record_save  # This already considers unlock_for_edit internally

                # Check if admin has specifically unlocked this record
                is_admin_unlocked = visit.unlock_for_edit

                # Determine edit permission:
                # 1. Current month records are always editable
                # 2. Past month records are ONLY editable if admin has unlocked them
                can_edit = is_current_month or is_admin_unlocked

                # Delete permission follows same logic as edit
                can_delete = is_current_month or is_admin_unlocked

                reason = None

                if not can_edit:
                    if not is_current_month and is_locked:
                        reason = "Past month records are locked. Please contact Admin to unlock."
                    elif not is_current_month and not is_admin_unlocked:
                        reason = "This is a past month record that hasn't been unlocked by admin."
                    elif visit.asm_state == 'verified':
                        reason = "Verified records cannot be edited."
                    elif visit.asm_state == 'submitted':
                        reason = "Record is under manager review."
                    else:
                        reason = "This record cannot be edited."

                # ===== LINE DATA =====
                for line in visit.line_ids:
                    line_items.append({
                        "line_id": line.id,
                        "month": line.month,
                        "category_id": line.category_id.id if line.category_id else None,
                        "category_name": line.category_id.name if line.category_id else None,
                        "product_id": line.product_id.id if line.product_id else None,
                        "product_name": line.product_id.display_name if line.product_id else None,
                        "rate_type": line.rate_type,
                        "unit_price": line.price_unit,
                        "quantity": line.product_qty,
                        "amount": line.amount,
                        "discount_percent": line.discount_percent
                    })

                visit_data = {
                    "mr_doctor_id": visit.id,
                    "reference": visit.name,
                    "mr_id": visit.mr_id.id if visit.mr_id else None,
                    "mr_name": visit.mr_id.name if visit.mr_id else None,
                    "doctor_id": visit.doctor_id.id if visit.doctor_id else None,
                    "doctor_name": visit.doctor_id.name if visit.doctor_id else None,
                    "doctor_unique_id": visit.doc_unique_id,
                    "territory_id": visit.territory_id.id if visit.territory_id else None,
                    "territory_name": visit.territory_id.name if visit.territory_id else None,
                    "status": visit.asm_state,
                    "total_lines": len(line_items),
                    "lines": line_items,

                    # ===== PERMISSION FLAGS =====
                    "can_edit": can_edit,
                    "can_delete": can_delete,
                    "is_locked": is_locked,
                    "is_current_month": is_current_month,
                    "is_admin_unlocked": is_admin_unlocked,
                    "record_save": visit.record_save,  # This shows the computed lock status
                    "unlock_for_edit": visit.unlock_for_edit,
                    "bulk_unlock_id": visit.bulk_unlock_id,  # Include bulk operation info
                    "bulk_unlocked_by": visit.bulk_unlocked_by.name if visit.bulk_unlocked_by else None,
                    "bulk_unlock_date": visit.bulk_unlock_date.strftime('%Y-%m-%d %H:%M:%S') if visit.bulk_unlock_date else None,
                    "reason": reason
                }

                if visit.asm_state == 'rejected':
                    visit_data["rejection_reason"] = visit.rejection_reason or ""

                visits_data.append(visit_data)

            return Response(json.dumps({
                "success": True,
                "total_visits": len(visits_data),
                "visits": visits_data
            }, default=str), content_type='application/json')

        except Exception as e:
            _logger.exception("Error in /list_mr_doctor_visits API")
            return Response(json.dumps({
                "success": False,
                "message": str(e)
            }), content_type='application/json')
        
############### API for Verification workflow by Managers ########################## 
class MRDoctorVerifyActionAPI(http.Controller):

    @http.route('/mr_doctor_verify_action', type='http', auth='public', cors='*', methods=['POST'], csrf=False)

    def mr_doctor_verify_action(self, **kwargs):

        user, error_response = validate_api_request(request, kwargs)
        if error_response:
            return error_response

        # Only sales_manager can verify
        if not user.has_group('ubik_app.group_sales_manager'):
            return Response(json.dumps({
                "success": False,
                "message": "You are not allowed to verify records"
            }), content_type='application/json')

        visit_id = kwargs.get('mr_doctor_id')
        action_type = kwargs.get('action')
        reason = kwargs.get('reason')

        if not visit_id or not action_type:
            return Response(json.dumps({
                "success": False,
                "message": "mr_doctor_id and action are required"
            }), content_type='application/json')

        visit = request.env['mr.doctor'].sudo().browse(int(visit_id))

        if not visit.exists():
            return Response(json.dumps({
                "success": False,
                "message": "Invalid record"
            }), content_type='application/json')

        # Only assigned manager can verify
        if visit.manager_id.id != user.id:
            return Response(json.dumps({
                "success": False,
                "message": "You are not assigned manager for this record"
            }), content_type='application/json')

        # Only submitted records can be verified
        if visit.asm_state != 'submitted':
            return Response(json.dumps({
                "success": False,
                "message": f"Only submitted records can be verified. Current status: {visit.asm_state}"
            }), content_type='application/json')

        if action_type == 'accept':

                visit = visit.with_user(user)
                visit.action_verify_by_asm()

                return Response(json.dumps({
                    "success": True,
                    "message": "Record accepted successfully",
                    "status": visit.asm_state
                }), content_type='application/json')

        elif action_type == 'reject':

                if not reason:
                    return Response(json.dumps({
                        "success": False,
                        "message": "Rejection reason is required"
                    }), content_type='application/json')

                visit = visit.with_user(user)
                visit.rejection_reason = reason
                visit.action_reject_by_asm()

                return Response(json.dumps({
                    "success": True,
                    "message": "Record rejected successfully",
                    "status": visit.asm_state
                }), content_type='application/json')
        else:
            return Response(json.dumps({
                "success": False,
                "message": "Invalid action. Use 'accept' or 'reject'"
            }), content_type='application/json')

############### API: List MRs under logged-in Manager ##########################
class ManagerMRListAPI(http.Controller):

    @http.route('/manager_mr_list', type='http', auth='public',cors='*', methods=['POST'], csrf=False)
    def get_manager_mr_list(self, **kwargs):

        # Validate token
        user, error_response = validate_api_request(request, kwargs)
        if error_response:
            return error_response

        # Check if user is sales manager
        if not user.has_group('ubik_app.group_sales_manager'):
            return Response(json.dumps({
                "success": False,
                "message": "You are not authorized to view MR list"
            }), content_type='application/json')

        # Get employee record of manager
        manager_employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', user.id)], limit=1)

        if not manager_employee:
            return Response(json.dumps({
                "success": False,
                "message": "Manager employee record not found"
            }), content_type='application/json')

        # Fetch MRs reporting to this manager
        mr_employees = request.env['hr.employee'].sudo().search([
            ('parent_id', '=', manager_employee.id),
            ('user_id', '!=', False)
        ])

        if not mr_employees:
            return Response(json.dumps({
                "success": True,
                "count": 0,
                "mrs": []
            }), content_type='application/json')

        data = []

        for emp in mr_employees:
            data.append({
                "employee_id": emp.id,
                "employee_name": emp.name,
                "user_id": emp.user_id.id if emp.user_id else None,
                "user_name": emp.user_id.name if emp.user_id else None,
                "job_position": emp.job_id.name if emp.job_id else None,
                "work_email": emp.work_email,
                "mobile": emp.mobile_phone,
            })

        return Response(json.dumps({
            "success": True,
            "count": len(data),
            "mrs": data
        }), content_type='application/json')

############### API to list selected MR records by Manager ########################## 
class ManagerMRDoctorVisitsAPI(http.Controller):

    @http.route('/manager_selected_mr_visits_list', type='http',
                auth='public', cors='*', methods=['POST'], csrf=False)
    def get_mr_doctor_visits_by_manager(self, **kwargs):

        # Validate token (should return logged-in manager)
        user, error_response = validate_api_request(request, kwargs)
        if error_response:
            return error_response

        # Must be sales manager
        if not user.has_group('ubik_app.group_sales_manager'):
            return Response(json.dumps({
                "success": False,
                "message": "You are not authorized to view MR records"
            }), content_type='application/json')

        selected_user_id = kwargs.get('selected_user_id')

        if not selected_user_id:
            return Response(json.dumps({
                "success": False,
                "message": "selected_user_id is required"
            }), content_type='application/json')

        selected_user = request.env['res.users'].sudo().browse(int(selected_user_id))

        if not selected_user.exists():
            return Response(json.dumps({
                "success": False,
                "message": "Invalid selected user"
            }), content_type='application/json')

        # Get employees
        manager_employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', user.id)], limit=1)

        mr_employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', selected_user.id)], limit=1)

        if not manager_employee or not mr_employee:
            return Response(json.dumps({
                "success": False,
                "message": "Employee record not found"
            }), content_type='application/json')

        # Check reporting
        if mr_employee.parent_id.id != manager_employee.id:
            return Response(json.dumps({
                "success": False,
                "message": "This MR does not report to you"
            }), content_type='application/json')

        # Fetch visits
        mr_visits = request.env['mr.doctor'].sudo().search([
            ('mr_id', '=', selected_user.id)
        ], order='create_date desc')

        visits_data = []

        for visit in mr_visits:
            line_items = []
            for line in visit.line_ids:
                line_items.append({
                    "line_id": line.id,
                    "month": line.month,
                    "category_name": line.category_id.name if line.category_id else None,
                    "product_name": line.product_id.display_name if line.product_id else None,
                    "rate_type": line.rate_type,
                    "unit_price": line.price_unit,
                    "quantity": line.product_qty,
                    "amount": line.amount,
                })

            visit_dict = {
                "mr_doctor_id": visit.id,
                "territory_id": visit.territory_id.id if visit.territory_id else None,
                "territory_name": visit.territory_id.name if visit.territory_id.name else None,
                "reference": visit.name,
                "doctor_name": visit.doctor_id.name,
                "status": visit.asm_state,
                "lines": line_items
            }

            # Add rejection reason only if rejected
            if visit.asm_state == 'rejected':
                visit_dict["rejection_reason"] = visit.rejection_reason or ""

            visits_data.append(visit_dict)

        return Response(json.dumps({
            "success": True,
            "count": len(visits_data),
            "visits": visits_data
        }, default=str), content_type='application/json')

############### API to check if today's first record for MR: For showing declaration text only once in a day ##########################
class MRFirstRecordCheckAPI(http.Controller):

    @http.route('/check_today_first_record', type='http', auth='public', cors='*', methods=['POST'], csrf=False)
    
    def check_today_first_record(self, **kwargs):
        """
        API to check if this is the first record being created today for the logged-in user.
        Returns: 
            - is_first_today: 1 if this is the first record today, 0 if records already exist
            - declaration_required: Same as is_first_today (for clarity in app)
            - record_count_today: Number of records created today
        """
        try:
            # Validate token & user
            user, error_response = validate_api_request(request, kwargs)
            if error_response:
                return error_response

            # Get today's date range (start and end of day)
            today = fields.Datetime.now()
            start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Count records created today for this user
            today_records_count = request.env['mr.doctor'].sudo().search_count([
                ('mr_id', '=', user.id),
                ('create_date', '>=', start_of_day),
                ('create_date', '<=', end_of_day)
            ])

            # Determine if this is the first record today
            is_first_today = 1 if today_records_count == 0 else 0

            return Response(
                json.dumps({
                    "success": True,
                    "is_first_today": is_first_today,
                    "declaration_required": is_first_today,  # Alias for clarity
                    "record_count_today": today_records_count,
                    "message": "First record today" if is_first_today else "Records already exist today"
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.exception("Error in /check_today_first_record API")
            return Response(
                json.dumps({
                    "success": False,
                    "message": str(e),
                    "is_first_today": 0,  # Default to not showing declaration on error
                    "declaration_required": 0
                }),
                content_type='application/json'
            )

############### API to Edit MR Doctor Visit Record ##########################
class MRDoctorEditAPI(http.Controller):

    @http.route('/edit_mr_doctor_visit_record', type='http', auth='public', cors='*', methods=['POST'], csrf=False)
    def edit_mr_doctor_visit(self, **kwargs):
        """
        API to edit an existing MR doctor visit record.
        Uses line index instead of line_id.
        """

        try:
            # Validate token & user
            user, error_response = validate_api_request(request, kwargs)
            if error_response:
                return error_response

            # Employee validation
            employee = request.env['hr.employee'].sudo().search(
                [('user_id', '=', user.id)], limit=1)

            if not employee:
                return Response(json.dumps({
                    "success": False,
                    "message": "Employee not linked to this user"
                }), content_type='application/json')

            if employee.job_id.name not in ['MR', 'ASM', 'RSM']:
                return Response(json.dumps({
                    "success": False,
                    "message": "Only MR, ASM or RSM can edit visit records"
                }), content_type='application/json')

            # Parameters
            mr_doctor_id = kwargs.get('mr_doctor_id')
            territory_id = kwargs.get('territory_id')
            doctor_id = kwargs.get('doctor_id')

            if not mr_doctor_id:
                return Response(json.dumps({
                    "success": False,
                    "message": "mr_doctor_id is required"
                }), content_type='application/json')

            mr_doctor = request.env['mr.doctor'].sudo().browse(int(mr_doctor_id))

            if not mr_doctor.exists():
                return Response(json.dumps({
                    "success": False,
                    "message": "Record not found"
                }), content_type='application/json')

            # Security check
            if mr_doctor.mr_id.id != user.id:
                return Response(json.dumps({
                    "success": False,
                    "message": "You can only edit your own records"
                }), content_type='application/json')

            # Lock check
            current_month = datetime.today().strftime('%Y-%m')
            is_current_month = all(line.month == current_month for line in mr_doctor.line_ids)

            if not is_current_month:
                if mr_doctor.record_save and not mr_doctor.unlock_for_edit:
                    return Response(json.dumps({
                        "success": False,
                        "message": "Past month records are locked. Please contact Admin to unlock."
                    }), content_type='application/json')

            # Territory validation
            if territory_id:
                if int(territory_id) not in employee.territory_ids.ids:
                    return Response(json.dumps({
                        "success": False,
                        "message": "Territory not assigned to you"
                    }), content_type='application/json')

            # Doctor validation
            if doctor_id:
                doctor = request.env['res.partner'].sudo().browse(int(doctor_id))
                if not doctor.is_doctor:
                    return Response(json.dumps({
                        "success": False,
                        "message": "Invalid doctor"
                    }), content_type='application/json')

            # Update header
            header_vals = {}

            if territory_id:
                header_vals['territory_id'] = int(territory_id)

            if doctor_id:
                header_vals['doctor_id'] = int(doctor_id)
                doctor = request.env['res.partner'].sudo().browse(int(doctor_id))
                header_vals['doc_unique_id'] = doctor.doc_unique_id

            if header_vals:
                mr_doctor.write(header_vals)

            # Existing lines ordered
            existing_lines = mr_doctor.line_ids.sorted('id')

            index = 0
            territory_id_to_use = territory_id or mr_doctor.territory_id.id

            while True:

                category_id = kwargs.get(f'line_category_id[{index}]')
                product_id = kwargs.get(f'line_product_id[{index}]')

                if not category_id or not product_id:
                    break

                rate_type = kwargs.get(f'line_rate_type[{index}]')
                qty = float(kwargs.get(f'line_qty[{index}]', 1))
                price = float(kwargs.get(f'line_price[{index}]', 0))
                # month = kwargs.get(f'line_month[{index}]') or datetime.today().strftime('%Y-%m')
                existing_month = existing_lines[index].month if index < len(existing_lines) else None

                month = kwargs.get(f'line_month[{index}]') or existing_month or datetime.today().strftime('%Y-%m')

                product = request.env['product.template'].sudo().browse(int(product_id))

                if not product.exists():
                    return Response(json.dumps({
                        "success": False,
                        "message": f"Invalid product_id: {product_id}"
                    }), content_type='application/json')

                # Territory validation
                if product.is_territory_specific_product:
                    if int(territory_id_to_use) not in product.allowed_territory_ids.ids:
                        return Response(json.dumps({
                            "success": False,
                            "message": f"Product '{product.display_name}' is not allowed in the selected territory"
                        }), content_type='application/json')

                if rate_type not in ['ptr_rate', 'custom_rate']:
                    return Response(json.dumps({
                        "success": False,
                        "message": f"Invalid rate type at line {index}"
                    }), content_type='application/json')

                if rate_type == 'ptr_rate':
                    price = product.list_price

                if rate_type == 'custom_rate' and price > product.list_price:
                    return Response(json.dumps({
                        "success": False,
                        "message": f"Custom price cannot exceed PTR rate for product {product.display_name}"
                    }), content_type='application/json')

                line_vals = {
                    'mr_doctor_id': mr_doctor.id,
                    'category_id': int(category_id),
                    'product_id': product.id,
                    'rate_type': rate_type,
                    'price_unit': price,
                    'product_qty': qty,
                    'month': month,
                }

                # UPDATE USING INDEX
                if index < len(existing_lines):
                    existing_lines[index].sudo().write(line_vals)

                # CREATE NEW LINE
                else:
                    request.env['mr.doctor.line'].sudo().create(line_vals)

                index += 1

            # Workflow
            # if not user.has_group('base.group_system'):
            #     if mr_doctor.asm_state in ['verified', 'rejected']:
            #         mr_doctor.with_user(user).action_submit_to_asm()

            # if mr_doctor.unlock_for_edit and not user.has_group('base.group_system'):
            #     mr_doctor.with_user(user).action_submit_to_asm()

            if not user.has_group('base.group_system'):
                # If record was unlocked and edited
                if mr_doctor.unlock_for_edit:
                    mr_doctor.sudo().write({
                        'asm_state': 'draft'
                    })
                    mr_doctor.with_user(user).action_submit_to_asm()

                # If previously verified or rejected
                elif mr_doctor.asm_state in ['verified', 'rejected']:
                    mr_doctor.with_user(user).action_submit_to_asm()

            return Response(json.dumps({
                "success": True,
                "message": "Record updated successfully",
                "mr_doctor_id": mr_doctor.id,
                "reference": mr_doctor.name,
                "status": mr_doctor.asm_state
            }), content_type='application/json')

        except Exception as e:
            _logger.exception("Error in /edit_mr_doctor_visit_record API")
            return Response(json.dumps({
                "success": False,
                "message": str(e)
            }), content_type='application/json')

############### API to Delete MR Doctor Visit Record ##########################
class MRDoctorDeleteAPI(http.Controller):

    @http.route('/delete_mr_doctor_visit_record', type='http', auth='public', cors='*', methods=['POST'], csrf=False)
    def delete_mr_doctor_visit(self, **kwargs):
        """
        API to delete a product line from MR doctor visit record.
        Record itself will NOT be deleted.
        """

        try:
            # Validate token & user
            user, error_response = validate_api_request(request, kwargs)
            if error_response:
                return error_response

            # Employee validation
            employee = request.env['hr.employee'].sudo().search(
                [('user_id', '=', user.id)], limit=1)

            if not employee:
                return Response(json.dumps({
                    "success": False,
                    "message": "Employee not linked to this user"
                }), content_type='application/json')

            if employee.job_id.name not in ['MR', 'ASM', 'RSM']:
                return Response(json.dumps({
                    "success": False,
                    "message": "Only MR, ASM or RSM can delete visit records"
                }), content_type='application/json')

            # Parameters
            mr_doctor_id = kwargs.get('mr_doctor_id')
            line_index = kwargs.get('line_index')
            confirmation = kwargs.get('confirmation', '').lower()

            if not mr_doctor_id:
                return Response(json.dumps({
                    "success": False,
                    "message": "mr_doctor_id is required"
                }), content_type='application/json')

            if line_index is None:
                return Response(json.dumps({
                    "success": False,
                    "message": "line_index is required to delete a product line"
                }), content_type='application/json')

            # Fetch record
            mr_doctor = request.env['mr.doctor'].sudo().browse(int(mr_doctor_id))

            if not mr_doctor.exists():
                return Response(json.dumps({
                    "success": False,
                    "message": "Record not found"
                }), content_type='application/json')

            # Security check
            if mr_doctor.mr_id.id != user.id:
                return Response(json.dumps({
                    "success": False,
                    "message": "You can only delete your own records"
                }), content_type='application/json')

            # Lock check
            current_month = datetime.today().strftime('%Y-%m')
            is_current_month = all(line.month == current_month for line in mr_doctor.line_ids)

            if not is_current_month:
                if mr_doctor.record_save and not mr_doctor.unlock_for_edit:
                    return Response(json.dumps({
                        "success": False,
                        "message": "Past month records are locked. Please contact Admin to unlock."
                    }), content_type='application/json')

            # Confirmation check
            if confirmation != 'yes':
                return Response(json.dumps({
                    "success": False,
                    "message": "Please confirm deletion with confirmation='yes'",
                    "requires_confirmation": True
                }), content_type='application/json')

            # Get lines in stable order
            lines = mr_doctor.line_ids.sorted('id')

            index = int(line_index)

            if index < 0 or index >= len(lines):
                return Response(json.dumps({
                    "success": False,
                    "message": "Invalid line index"
                }), content_type='application/json')

            line_to_delete = lines[index]

            line_info = {
                "line_id": line_to_delete.id,
                "product": line_to_delete.product_id.display_name,
                "qty": line_to_delete.product_qty
            }

            # Delete only the line
            line_to_delete.sudo().unlink()

            return Response(json.dumps({
                "success": True,
                "message": "Product line deleted successfully",
                "deleted_line": line_info,
                "remaining_lines": len(mr_doctor.line_ids)
            }), content_type='application/json')

        except Exception as e:
            _logger.exception("Error in /delete_mr_doctor_visit_record API")
            return Response(json.dumps({
                "success": False,
                "message": str(e)
            }), content_type='application/json')

