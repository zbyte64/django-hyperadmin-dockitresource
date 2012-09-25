from hyperadmin.resources.crud.crud import CRUDResource
from dockit import forms

from dockitresource import views
from dockitresource.changelist import DocumentChangeList

class DocumentResource(CRUDResource):
    #TODO support the following:
    #raw_id_fields = ()
    fields = None
    exclude = []
    #fieldsets = None
    #filter_vertical = ()
    #filter_horizontal = ()
    #radio_fields = {}
    #prepopulated_fields = {}
    formfield_overrides = {}
    #readonly_fields = ()
    #declared_fieldsets = None
    
    #save_as = False
    #save_on_top = False
    changelist_class = DocumentChangeList
    
    #list display options
    list_display_links = ()
    list_filter = ()
    list_select_related = False
    list_per_page = 100
    list_max_show_all = 200
    list_editable = ()
    search_fields = ()
    date_hierarchy = None
    
    list_view = views.DocumentListView
    add_view = views.DocumentCreateView
    detail_view = views.DocumentDetailView
    delete_view = views.DocumentDeleteView
    
    @property
    def document(self):
        return self.resource_adaptor
    
    @property
    def opts(self):
        return self.document._meta
    
    def get_app_name(self):
        return self.opts.app_label
    app_name = property(get_app_name)
    
    def get_resource_name(self):
        return self.opts.module_name
    resource_name = property(get_resource_name)
    
    def get_prompt(self):
        return self.resource_name
    
    def get_view_kwargs(self):
        kwargs = super(DocumentResource, self).get_view_kwargs()
        kwargs['document'] = self.document
        return kwargs
    
    def get_active_index(self, **kwargs):
        return self.get_queryset(user=self.state['auth'])
    
    def lookup_allowed(self, lookup, value):
        return True #TODO
    
    def get_queryset(self, user):
        queryset = self.resource_adaptor.objects.all()
        if not self.has_change_permission(user):
            queryset = queryset.none()
        return queryset
    
    def _get_schema_fields(self):
        for field in self.opts.fields.itervalues():
            if getattr(field, 'schema', None):
                yield (field, field.schema, False)
            elif getattr(field, 'subfield', None) and getattr(field.subfield, 'schema', None):
                yield (field, field.subfield.schema, True)
    
    def _get_static_schema_fields(self):
        fields = list()
        for field, schema, many in self._get_schema_fields():
            if not schema._meta.is_dynamic():
                fields.append((field, schema, many))
        return fields
    
    def _get_noncomplex_fields(self):
        from dockit import schema
        #list fields of "primitives" are not considered complex enough
        for field in self.opts.fields.itervalues():
            if isinstance(field, schema.SchemaField) or isinstance(field, schema.GenericSchemaField):
                yield field
            elif isinstance(field, schema.ListField):
                if getattr(field.subfield, 'schema', None) or isinstance(field.subfield, schema.GenericSchemaField):
                    yield field
    
    def get_excludes(self):
        excludes = set(self.exclude)
        for field in self._get_noncomplex_fields():
            excludes.add(field.name)
        return list(excludes)
    
    def get_form_class(self):
        if self.form_class:
            return self.form_class
        class AdminForm(forms.DocumentForm):
            class Meta:
                document = self.document
                exclude = self.get_excludes()
                #TODO formfield overides
                #TODO fields
        return AdminForm
    
    def get_html_type_from_field(self, field):
        from dockit.forms import widgets
        widget = field.field.widget
        if isinstance(widget, widgets.PrimitiveListWidget):
            return 'list'
        return super(DocumentResource, self).get_html_type_from_field(field)

