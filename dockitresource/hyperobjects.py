from django.utils.encoding import force_unicode
from django import forms

from hyperadmin.resources.hyperobjects import ResourceItem
from hyperadmin.apirequests import Namespace
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

class DotpathResourceSubitem(ResourceItem):
    def __init__(self, dotpath=None, subobject=None, **kwargs):
        super(DotpathResourceSubitem, self).__init__(**kwargs)
        assert dotpath
        self.dotpath = dotpath
        self._subobject = subobject
    
    def get_form_class(self):
        if self.form_class is not None:
            return self.form_class
        return self.resource.get_form_class(dotpath=self.dotpath, subobject=self.subobject)
    
    @property
    def subobject(self):
        if not self._subobject:
            val = self.instance
            self._subobject = val.dot_notation_to_value(self.dotpath)
        return self._subobject

class DotpathResourceItem(DotpathResourceSubitem):
    def get_resource_items(self):
        if self.state.is_sublisting:
            instances = self.subobject
            dotpath = self.dotpath
            ret = list()
            for index, subobject in enumerate(instances):
                subdotpath = '%s.%s' % (dotpath, index)
                ret.append(self.endpoint.get_resource_subitem(self.instance, dotpath=subdotpath, subobject=subobject))
            return ret
        return [self.endpoint.get_resource_subitem(self.instance, dotpath=self.dotpath)]

