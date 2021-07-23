# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class iessSectorialCommission(models.Model):
    _name = "iess.sectorial.commission"
    _description = _("Commission Iees")

    name = fields.Char("Name")
    code = fields.Char("Code")
    branch_ids = fields.One2many("iess.sectorial.branch", "commission_id", string="Branch")

class iessSectorialBranch(models.Model):
    _name = "iess.sectorial.branch"
    _description = _("Branch Iess")

    name = fields.Char("Name")
    code = fields.Char("Code")
    commission_id = fields.Many2one("iess.sectorial.commission", "Commission")
    job_ids = fields.One2many("iess.sectorial.job", "branch_id", string="Job")

class iessSectorialJob(models.Model):
    _name = "iess.sectorial.job"
    _description = _("Job Iess")

    name = fields.Char("Name")
    code = fields.Char("Code")
    value = fields.Float("Value")
    branch_id = fields.Many2one("iess.sectorial.branch", "Branch")