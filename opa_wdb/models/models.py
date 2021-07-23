import logging
from collections import defaultdict
from odoo import api, models, fields
_logger = logging.getLogger(__name__)

class Empty(object):
    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            _logger.log(logging.INFO, 'Its not active wdb')
            setattr(self, name, hasattr(self, name))
        return wrapper

class BaseModelExtend(models.AbstractModel):
    _name = 'basemodel.extend'

    def _register_hook(self):
        '''
        Register method in BaseModel
        >>> self.wdb.set_trace()
        '''
        def _wdb():
            try:
                import wdb
                return wdb
            except ImportError:
                return Empty()

        models.BaseModel.wdb = _wdb()
        return super(BaseModelExtend, self)._register_hook()