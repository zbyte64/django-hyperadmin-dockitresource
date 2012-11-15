from django.utils.encoding import force_unicode
from django import forms

from hyperadmin.hyperobjects import Namespace, ResourceItem
from hyperadmin.resources.crud.hyperobjects import ListResourceItem


class DotpathListForm(forms.Form):
    '''
    hyperadmin knows how to serialize forms, not models.
    So for the list display we need a form
    '''
    
    def __init__(self, **kwargs):
        self.instance = kwargs.pop('instance', None)
        self.resource = kwargs.pop('resource')
        super(DotpathListForm, self).__init__(**kwargs)
        #TODO this is all wrong
        label = self.resource.resource_name
        display = 'object'
        self.fields[display] = forms.CharField(label=label)
        if self.instance:
            self.initial[display] = force_unicode(self.instance)
        else:
            pass

class DotpathListResourceItem(ListResourceItem):
    form_class = DotpathListForm


class DotpathNamespace(Namespace):
    pass

class DotpathResourceItem(ResourceItem):
    def __init__(self, dotpath=None, **kwargs):
        super(DotpathResourceItem, self).__init__(**kwargs)
        assert dotpath
        self.dotpath = dotpath
    
    def get_form_class(self):
        if self.form_class is not None:
            return self.form_class
        return self.resource.get_form_class(dotpath=self.dotpath, subobject=self.subobject)
    
    @property
    def subobject(self):
        if self.dotpath:
            val = self.instance
            return val.dot_notation_to_value(self.dotpath)
        return self.instance

