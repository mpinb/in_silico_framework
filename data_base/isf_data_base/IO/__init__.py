import logging
import sys
sys.modules['isf_data_base.IO'] = sys.modules[__name__]

logger = logging.getLogger("ISF").getChild(__name__)