from django import template
import json
from django.core.serializers.json import DjangoJSONEncoder

register = template.Library()

@register.filter(is_safe=True)
def jsonify(obj):
    return json.dumps(obj, cls=DjangoJSONEncoder)
