# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class EimsLog(models.Model):
    _name = 'eims.log'
    _description = 'EIMS Integration Log'
    _order = 'create_date desc'
    _rec_name = 'display_name'
    
    # Main fields
    move_id = fields.Many2one(
        'account.move', 
        string='Invoice',
        required=True,
        ondelete='cascade',
        help='The invoice that was processed'
    )
    invoice_number = fields.Char(
        string='Invoice Number',
        related='move_id.name',
        store=True,
        help='Invoice number for quick reference'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='move_id.company_id',
        store=True,
        help='Company that owns the invoice'
    )
    
    # Request/Response data
    request_json = fields.Text(
        string='Request JSON',
        help='Full JSON payload sent to EIMS'
    )
    response_json = fields.Text(
        string='Response JSON',
        help='Full JSON response received from EIMS'
    )
    
    # Status and error information
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('ok', 'Success'),
        ('failed', 'Failed')
    ], string='Status', default='draft', required=True)
    
    error_text = fields.Text(
        string='Error Message',
        help='Detailed error message if the request failed'
    )
    error_code = fields.Char(
        string='Error Code',
        help='EIMS error code if available'
    )
    
    # EIMS response data
    irn = fields.Char(
        string='IRN',
        help='Invoice Reference Number from EIMS'
    )
    qr_code = fields.Binary(
        string='QR Code',
        help='QR code image received from EIMS'
    )
    qr_data = fields.Text(
        string='QR Data',
        help='Raw QR code data from EIMS'
    )
    
    # Timestamps
    datetime = fields.Datetime(
        string='Date/Time',
        default=fields.Datetime.now,
        required=True,
        help='When this log entry was created'
    )
    ack_date = fields.Datetime(
        string='Acknowledgment Date',
        help='When EIMS acknowledged the invoice'
    )
    
    # Technical details
    http_status_code = fields.Integer(
        string='HTTP Status Code',
        help='HTTP status code returned by EIMS API'
    )
    response_time_ms = fields.Integer(
        string='Response Time (ms)',
        help='Time taken for the API request in milliseconds'
    )
    
    # Computed fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    has_error = fields.Boolean(
        string='Has Error',
        compute='_compute_has_error',
        help='Whether this log entry contains an error'
    )
    is_success = fields.Boolean(
        string='Is Success',
        compute='_compute_is_success',
        help='Whether this log entry represents a successful operation'
    )
    
    @api.depends('move_id', 'datetime', 'state')
    def _compute_display_name(self):
        """Compute display name for the log entry"""
        for record in self:
            if record.move_id and record.datetime:
                record.display_name = f"{record.move_id.name} - {record.datetime.strftime('%Y-%m-%d %H:%M')} ({record.state})"
            else:
                record.display_name = f"EIMS Log - {record.state}"
    
    @api.depends('state', 'error_text')
    def _compute_has_error(self):
        """Check if this log entry has an error"""
        for record in self:
            record.has_error = record.state == 'failed' or bool(record.error_text)
    
    @api.depends('state')
    def _compute_is_success(self):
        """Check if this log entry represents success"""
        for record in self:
            record.is_success = record.state == 'ok'
    
    @api.model
    def create_log_entry(self, move_id, request_data=None, response_data=None, 
                        state='draft', error_text=None, error_code=None, 
                        irn=None, qr_data=None, http_status_code=None, 
                        response_time_ms=None):
        """Helper method to create a log entry"""
        vals = {
            'move_id': move_id,
            'state': state,
            'datetime': fields.Datetime.now(),
        }
        
        if request_data:
            vals['request_json'] = json.dumps(request_data, indent=2) if isinstance(request_data, dict) else str(request_data)
        
        if response_data:
            vals['response_json'] = json.dumps(response_data, indent=2) if isinstance(response_data, dict) else str(response_data)
        
        if error_text:
            vals['error_text'] = error_text
        
        if error_code:
            vals['error_code'] = error_code
        
        if irn:
            vals['irn'] = irn
            vals['ack_date'] = fields.Datetime.now()
        
        if qr_data:
            vals['qr_data'] = qr_data
        
        if http_status_code:
            vals['http_status_code'] = http_status_code
        
        if response_time_ms:
            vals['response_time_ms'] = response_time_ms
        
        return self.create(vals)
    
    def action_view_request_json(self):
        """View request JSON in a popup"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request JSON'),
            'res_model': 'eims.log',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'show_request_json': True}
        }
    
    def action_view_response_json(self):
        """View response JSON in a popup"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Response JSON'),
            'res_model': 'eims.log',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'show_response_json': True}
        }
    
    def action_retry_invoice(self):
        """Retry sending the invoice to EIMS"""
        self.ensure_one()
        if self.move_id:
            try:
                # Clear previous error status
                self.move_id.write({
                    'eims_status': 'draft',
                    'eims_last_error': False
                })
                
                # Retry the EIMS integration
                self.move_id.send_to_eims()
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Retry Initiated'),
                        'message': _('Invoice %s is being retried for EIMS integration') % self.move_id.name,
                        'type': 'info',
                        'sticky': False,
                    }
                }
            except Exception as e:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Retry Failed'),
                        'message': _('Could not retry invoice: %s') % str(e),
                        'type': 'danger',
                        'sticky': True,
                    }
                }
    
    @api.model
    def cleanup_old_logs(self, days_to_keep=90):
        """Clean up old log entries to prevent database bloat"""
        from datetime import timedelta
        cutoff_date = fields.Datetime.now() - timedelta(days=days_to_keep)
        old_logs = self.search([
            ('create_date', '<', cutoff_date),
            ('state', 'in', ['ok', 'failed'])  # Only clean up completed logs
        ])
        
        if old_logs:
            count = len(old_logs)
            old_logs.unlink()
            _logger.info("Cleaned up %d old EIMS log entries", count)
            return count
        return 0
    
    @api.model
    def perform_health_check(self):
        """Perform EIMS system health check"""
        try:
            # Check recent success rate
            from datetime import timedelta
            last_24h = fields.Datetime.now() - timedelta(hours=24)
            
            recent_logs = self.search([
                ('datetime', '>=', last_24h)
            ])
            
            if recent_logs:
                success_count = len(recent_logs.filtered(lambda l: l.state == 'ok'))
                total_count = len(recent_logs)
                success_rate = (success_count / total_count) * 100
                
                _logger.info("EIMS Health Check - Success Rate (24h): %.2f%% (%d/%d)", 
                           success_rate, success_count, total_count)
                
                # Alert if success rate is below 80%
                if success_rate < 80:
                    _logger.warning("EIMS Health Check - Low success rate: %.2f%%", success_rate)
                    
                    # Send notification to EIMS managers
                    self._send_health_alert(success_rate, total_count, success_count)
            else:
                _logger.info("EIMS Health Check - No recent activity")
                
        except Exception as e:
            _logger.error("EIMS Health Check failed: %s", str(e))
    
    def _send_health_alert(self, success_rate, total_count, success_count):
        """Send health alert to EIMS managers"""
        try:
            managers = self.env['res.users'].search([
                ('groups_id', 'in', self.env.ref('eims_integration.group_eims_manager').id)
            ])
            
            if managers:
                message = f"""
EIMS Health Alert

Success Rate (24h): {success_rate:.2f}%
Successful Integrations: {success_count}
Total Integrations: {total_count}

Please check the EIMS logs for details.
                """
                
                # Create a mail message
                self.env['mail.message'].create({
                    'subject': 'EIMS Health Alert - Low Success Rate',
                    'body': message,
                    'message_type': 'notification',
                    'partner_ids': [(6, 0, managers.mapped('partner_id').ids)],
                })
                
        except Exception as e:
            _logger.error("Failed to send EIMS health alert: %s", str(e))
    
    @api.model
    def get_integration_stats(self, days=30):
        """Get EIMS integration statistics for the last N days"""
        from datetime import timedelta
        start_date = fields.Datetime.now() - timedelta(days=days)
        
        logs = self.search([
            ('datetime', '>=', start_date)
        ])
        
        stats = {
            'total': len(logs),
            'success': len(logs.filtered(lambda l: l.state == 'ok')),
            'failed': len(logs.filtered(lambda l: l.state == 'failed')),
            'pending': len(logs.filtered(lambda l: l.state in ['pending', 'sent'])),
            'success_rate': 0,
            'avg_response_time': 0,
        }
        
        if stats['total'] > 0:
            stats['success_rate'] = (stats['success'] / stats['total']) * 100
            
            response_times = logs.filtered(lambda l: l.response_time_ms).mapped('response_time_ms')
            if response_times:
                stats['avg_response_time'] = sum(response_times) / len(response_times)
        
        return stats
    
    @api.model
    def get_error_summary(self, days=7):
        """Get summary of common errors"""
        from datetime import timedelta
        start_date = fields.Datetime.now() - timedelta(days=days)
        
        failed_logs = self.search([
            ('datetime', '>=', start_date),
            ('state', '=', 'failed')
        ])
        
        error_summary = {}
        for log in failed_logs:
            error_text = log.error_text or 'Unknown error'
            # Extract first line of error for grouping
            error_key = error_text.split('\n')[0][:100]
            error_summary[error_key] = error_summary.get(error_key, 0) + 1
        
        # Sort by frequency
        return sorted(error_summary.items(), key=lambda x: x[1], reverse=True)
