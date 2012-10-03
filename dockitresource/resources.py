from django.conf.urls.defaults import patterns, url, include

from hyperadmin.resources.crud.crud import CRUDResource
from hyperadmin.hyperobjects import Link

from dockit import forms
from dockit.schema import Schema

from dockitresource import views
from dockitresource.changelist import DocumentChangeList
from dockitresource.hyperobjects import DotpathState, DotpathNamespace

class BaseDocumentResource(CRUDResource):
    state_class = DotpathState
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
    list_per_page = 100
    list_max_show_all = 200
    
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
    
    def get_field(self, schema, dotpath):
        field = None
        if dotpath and self.state.item:
            obj = self.state.item.instance
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
    
    def get_active_object(self):
        if self.state.dotpath:
            val = self.state.item.instance
            return val.dot_notation_to_value(self.state.dotpath)
        return self.state.item.instance
    
    @property
    def schema(self):
        '''
        Retrieves the currently active schema, taking into account dynamic typing
        '''
        schema = None
        
        if self.state.dotpath:
            field = self.get_field(self.document, self.state.dotpath)
            if getattr(field, 'subfield', None):
                field = field.subfield
            if getattr(field, 'schema'):
                schema = field.schema
                if schema._meta.typed_field:
                    typed_field = schema._meta.fields[schema._meta.typed_field]
                    if self.state.params.get(schema._meta.typed_field, False):
                        key = self.state.params[schema._meta.typed_field]
                        schema = typed_field.schemas[key]
                    else:
                        obj = self.get_active_object()
                        if obj is not None and isinstance(obj, Schema):
                            schema = type(obj)
            else:
                assert False
        else:
            schema = self.document
        assert issubclass(schema, Schema)
        return schema
    
    def get_app_name(self):
        return self.opts.app_label
    app_name = property(get_app_name)
    
    def get_resource_name(self):
        return self.opts.module_name
    resource_name = property(get_resource_name)
    
    def get_prompt(self):
        return self.resource_name
    
    def get_view_kwargs(self):
        kwargs = super(BaseDocumentResource, self).get_view_kwargs()
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
        for field in self.schema._meta.fields.itervalues():
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
    
    def _get_complex_fields(self):
        from dockit import schema
        #list fields of "primitives" are not considered complex enough, but if it embeds a schema it is complex
        for field in self.schema._meta.fields.itervalues():
            if isinstance(field, schema.SchemaField) or isinstance(field, schema.GenericSchemaField):
                yield field
            elif isinstance(field, schema.ListField):
                if getattr(field.subfield, 'schema', None) or isinstance(field.subfield, schema.GenericSchemaField):
                    yield field
    
    def get_excludes(self):
        if self.state.dotpath:
            excludes = set()
        else:
            excludes = set(self.exclude)
        for field in self._get_complex_fields():
            excludes.add(field.name)
        return list(excludes)
    
    def get_form_class(self):
        if self.state.dotpath:
            pass #TODO
        elif self.form_class:
            return self.form_class
        class AdminForm(forms.DocumentForm):
            class Meta:
                document = self.document
                exclude = self.get_excludes()
                dotpath = self.state.dotpath
                #TODO formfield overides
                #TODO fields
        return AdminForm
    
    def get_html_type_from_field(self, field):
        from dockit.forms import widgets
        widget = field.field.widget
        if isinstance(widget, widgets.PrimitiveListWidget):
            return 'list'
        return super(BaseDocumentResource, self).get_html_type_from_field(field)
    
    def get_namespaces(self):
        namespaces = super(BaseDocumentResource, self).get_namespaces()
        if self.state.item is not None and self.state.get('view_class', None) == 'change_form':
            item = self.state.item
            
            for field in self._get_complex_fields():
                name = 'inline-%s' % field.name
                inline = self.fork_state()
                if self.state.dotpath:
                    dotpath = self.state.dotpath+'.'+field.name
                else:
                    dotpath = field.name
                print dotpath
                inline.state.dotpath =  dotpath #our state class recognizes this variable
                link = inline.get_item_link(item, url=inline.get_item_url(item)+inline.state.get_query_string())
                namespace = DotpathNamespace(name=name, link=link, state=inline.state)
                namespaces[name] = namespace
            
            print namespaces
        return namespaces
    
    def get_item_namespaces(self, item):
        namespaces = super(BaseDocumentResource, self).get_item_namespaces(item)
        print namespaces
        
        for field in self._get_complex_fields():
            name = 'inline-%s' % field.name
            inline = self.fork_state()
            if self.state.dotpath:
                dotpath = self.state.dotpath+'.'+field.name
            else:
                dotpath = field.name
            inline.state.dotpath =  dotpath #our state class recognizes this variable
            link = inline.get_item_link(item, url=inline.get_item_url(item)+inline.state.get_query_string())
            namespace = DotpathNamespace(name=name, link=link, state=inline.state)
            namespaces[name] = namespace
        print namespaces
        return namespaces
    
    #TODO delete with dotpaths

class TemporaryDocumentResource(BaseDocumentResource):
    '''
    create new documents and copy existing documents in the temporary collection
    once your changes are done the changes can be committed
    '''
    copy_form_class = None
    
    @property
    def temp_document(self):
        from dockit.models import create_temporary_document_class
        if not hasattr(self, '_temp_document'):
            self._temp_document = create_temporary_document_class(self.document)
        return self._temp_document
    
    def get_form_class(self):
        if self.state.dotpath:
            pass #TODO
        elif self.form_class:
            return self.form_class
        class AdminForm(forms.DocumentForm):
            class Meta:
                document = self.temp_document
                schema = self.schema
                exclude = self.get_excludes()
                dotpath = self.state.dotpath or None
                #TODO formfield overides
                #TODO fields
        return AdminForm
    
    def get_queryset(self, user):
        #TODO
        queryset = self.temp_document.objects.all()
        if not self.has_change_permission(user):
            queryset = queryset.none()
        return queryset
    
    def get_base_url_name(self):
        return '%s_%s_%s_' % (self.parent.app_name, self.parent.resource_name, 'tempdoc')
    
    #TODO create may make a copy of an existing document or start a new one
    def get_copy_url(self):
        return self.reverse('%scopy' % self.get_base_url_name())
    
    def get_commit_url(self, item):
        return self.reverse('%scommit' % self.get_base_url_name(), pk=item.instance.pk)
    
    def get_copy_form_class(self):
        return self.copy_form_class
    
    def get_copy_form_kwargs(self, item, **form_kwargs):
        form_kwargs['instance'] = item.instance
        return form_kwargs
    
    def get_copy_link(self, item, form_kwargs=None, **kwargs):
        if form_kwargs is None:
            form_kwargs = {}
        form_kwargs = self.get_copy_form_kwargs(item, **form_kwargs)
        link_kwargs = {'url':self.get_copy_url(),
                       'resource':self,
                       'on_submit':self.handle_copy_submission,
                       'method':'POST',
                       'form_class':self.get_copy_form_class(),
                       'form_kwargs':form_kwargs,
                       'prompt':'edit',
                       'rel':'edit',}
        update_link = Link(**link_kwargs)
        return update_link
    
    def handle_copy_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            resource_item = self.get_resource_item(instance)
            return self.get_item_link(resource_item)
        return link.clone(form=form)
    
    #TODO handle_commit_submission
    def get_commit_link(self, item, form_kwargs=None, **kwargs):
        link_kwargs = {'url':self.get_commit_url(item),
                       'resource':self,
                       'on_submit':self.handle_commit_submission,
                       'method':'POST',
                       'form_kwargs':form_kwargs,
                       'prompt':'edit',
                       'rel':'edit',}
        update_link = Link(**link_kwargs)
        return update_link
    
    def handle_commit_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            resource_item = self.get_resource_item(instance)
            return self.get_item_link(resource_item)
        return link.clone(form=form)

class DocumentResource(BaseDocumentResource):
    temporary_document_resoure_class = TemporaryDocumentResource
    
    def __init__(self, *args, **kwargs):
        super(DocumentResource, self).__init__(*args, **kwargs)
        self.temporary_document_resource = self.create_temporary_document_resource()
    
    def create_temporary_document_resource(self):
        cls = self.get_temporary_document_resource_class()
        return cls(resource_adaptor=self.resource_adaptor, site=self.site, parent_resource=self)
    
    def get_temporary_document_resource_class(self):
        return self.temporary_document_resoure_class
    
    def get_extra_urls(self):
        urlpatterns = super(DocumentResource, self).get_extra_urls()
        urlpatterns += patterns('',
            url(r'^tempdoc/',
                include(self.temporary_document_resource.urls)),
        )
        return urlpatterns

