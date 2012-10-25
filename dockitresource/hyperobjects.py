from django.utils.encoding import force_unicode
from django import forms

from hyperadmin.hyperobjects import State, Namespace, ResourceItem
from hyperadmin.resources.crud.hyperobjects import ListResourceItem

from dockit.schema import Schema


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

class DotpathState(State):
    def set_dotpath(self, val):
        self['dopath'] = val
    
    def get_dotpath(self):
        return self.get('dotpath', '')
    
    dotpath = property(get_dotpath, set_dotpath)
    
    def set_parent(self, val):
        self['parent'] = val
    
    def get_parent(self):
        return self.get('parent', None)
    
    parent = property(get_parent, set_parent)
    
    def set_subobject(self, val):
        self['subobject'] = val
    
    def get_subobject(self):
        if 'subobject' not in self and self.parent:
            if self.dotpath:
                val = self.parent.instance
                self.subobject = val.dot_notation_to_value(self.dotpath)
            else:
                self.subobject = self.parent.instance
        return self.get('subobject', None)
    
    subobject = property(get_subobject, set_subobject)
    
    def _get_field(self, schema, dotpath):
        #helper function that returns the field belonging to the dotpath
        field = None
        if dotpath and self.parent:
            obj = self.parent.instance
            field = obj.dot_notation_to_field(dotpath)
            if field is None:
                parent_path = dotpath.rsplit('.', 1)[0]
                print 'no field', dotpath, obj
                
                from dockit.schema.common import DotPathTraverser
                traverser = DotPathTraverser(parent_path)
                traverser.resolve_for_instance(obj)
                info = traverser.resolved_paths
                subschema = info[2]['field'].schema
                fields = subschema._meta.fields
                
                field = obj.dot_notation_to_field(parent_path)
                data = obj._primitive_data
                assert field
        return field
    
    def set_schema(self, val):
        self['schema'] = val
    
    def get_schema(self):
        '''
        Retrieves the currently active schema, taking into account dynamic typing
        '''
        if 'schema' not in self:
            schema = None
            if self.dotpath:
                field = self._get_field(self.resource.document, self.dotpath)
                if getattr(field, 'subfield', None):
                    field = field.subfield
                if getattr(field, 'schema', None):
                    schema = field.schema
                else:
                    #too generic?
                    assert False, str(self)
            else:
                if self.item:
                    schema = type(self.item.instance)
                else:
                    schema = self.resource.document
            
            if schema._meta.typed_field:
                typed_field = schema._meta.fields[schema._meta.typed_field]
                if self.params.get(schema._meta.typed_field, False):
                    key = self.params[schema._meta.typed_field]
                    schema = typed_field.schemas[key]
                else:
                    #type ambiguity?!?
                    obj = self.subobject
                    if obj is not None and isinstance(obj, Schema):
                        schema = type(obj)
                    else:
                        self['schema_select_field'] = typed_field
                        self['schema_select'] = typed_field.get_schema_choices()
                        #TODO this changes the add links to first provide a schema drop down
            
            self['schema'] = schema
            assert issubclass(schema, Schema)
        return self['schema']
    
    schema = property(get_schema, set_schema)
    
    @property
    def is_sublisting(self):
        from dockit import schema
        if not self.dotpath:
            return False
        field = self._get_field(self.resource.document, self.dotpath)
        return isinstance(field, schema.ListField)

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

