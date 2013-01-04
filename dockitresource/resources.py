from django.conf.urls.defaults import patterns, url, include

from hyperadmin.resources.crud.crud import CRUDResource
from hyperadmin.hyperobjects import Link

from dockit import forms

from dockitresource.hyperobjects import DotpathNamespace, DotpathResourceItem, DotpathListResourceItem, DotpathResourceSubitem
from dockitresource.states import DotpathEndpointState
from dockitresource.endpoints import DotpathCreateEndpoint, DotpathDetailEndpoint, DotpathDeleteEndpoint, ListEndpoint, CreateEndpoint, DetailEndpoint, DeleteEndpoint


class DocumentResourceMixin(object):
    state_class = DotpathEndpointState
    dotpath_resource = None
    
    @property
    def document(self):
        return self.resource_adaptor
    
    @property
    def schema(self):
        '''
        Retrieves the currently active schema, taking into account dynamic typing
        '''
        return self.state.schema
    
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
    
    def get_html_type_from_field(self, field):
        from dockit.forms import widgets
        widget = field.field.widget
        if isinstance(widget, widgets.PrimitiveListWidget):
            return 'list'
        return super(DocumentResourceMixin, self).get_html_type_from_field(field)
    
    def namespace_supports_field(self, field):
        from dockit import schema
        if ((isinstance(field, schema.ListField) and isinstance(field.subfield, schema.GenericSchemaField)) or
            isinstance(field, schema.GenericSchemaField)):
            return False
        return True
    
    def get_item_namespaces(self, item):
        namespaces = super(DocumentResourceMixin, self).get_item_namespaces(item)
        if self.dotpath_resource:
            base_dotpath = getattr(self.state, 'dotpath', '')
            for field in self._get_complex_fields():
                if not self.namespace_supports_field(field):
                    continue
                name = 'inline-%s' % field.name
                if base_dotpath:
                    dotpath = base_dotpath+'.'+field.name
                else:
                    dotpath = field.name
                #we forked but links is pointing somewhere else...
                #inline = self.dotpath_resource.fork_state(dotpath=dotpath, parent=item)
                #subitem = inline.get_resource_item(item.instance, dotpath=dotpath)
                #link = inline.get_item_link(subitem)
                #namespace = DotpathNamespace(name=name, link=link, state=inline.state)
                #namespaces[name] = namespace
                
                inline = self.dotpath_resource
                namespace = DotpathNamespace(name=name, endpoint=inline, state_data={'parent':item, 'dotpath':dotpath})
                try:
                    item = namespace.endpoint.get_resource_item(instance=item.instance, dotpath=dotpath)
                    assert item
                    namespace.endpoint.state['item'] = item
                except Exception as error:
                    print error
                    raise
                namespaces[name] = namespace
        return namespaces
    
    def get_queryset(self, user):
        queryset = self.resource_adaptor.objects.all()
        if not self.has_change_permission(user):
            queryset = queryset.none()
        return queryset
    
    @property
    def schema_select(self):
        return self.state.requires_schema_select
    
    def get_create_select_schema_form_class(self):
        from django import forms as djangoforms
        class SelectSchemaForm(djangoforms.Form):
            def __init__(self, **kwargs):
                self.instance = kwargs.pop('instance', None)
                super(SelectSchemaForm, self).__init__(**kwargs)
        
        typed_field = self.state.get_schema_select_field()
        key = typed_field.name
        SelectSchemaForm.base_fields[key] = djangoforms.ChoiceField(choices=typed_field.get_schema_choices())
        return SelectSchemaForm

class DotpathResource(DocumentResourceMixin, CRUDResource):
    #changelist_class = DotpathChangeList
    resource_item_class = DotpathResourceItem
    resource_subitem_class = DotpathResourceSubitem
    list_resource_item_class = DotpathListResourceItem
    
    def get_base_url_name(self):
        return '%s%s_' % (self.parent.get_base_url_name(), 'dotpath')
    
    def get_view_endpoints(self):
        endpoints = super(CRUDResource, self).get_view_endpoints()
        endpoints.extend([
            (DotpathCreateEndpoint, {}),
            (DotpathDetailEndpoint, {}),
            (DotpathDeleteEndpoint, {}),
        ])
        return endpoints
    
    def get_main_link_name(self):
        return 'update'
    
    def get_absolute_url(self):
        return self.link_prototypes['update'].get_url(item=self.state.item)
    
    def get_link(self, **kwargs):
        assert self.state.item
        #must include endpoint in kwargs
        link_kwargs = {'rel':'self',
                       'item':self.state.item,
                       'prompt':self.get_prompt(),}
        link_kwargs.update(kwargs)
        return self.link_prototypes['update'].get_link(**link_kwargs)
    
    def get_create_schema_link(self, item, form_kwargs=None, **kwargs):
        if form_kwargs is None:
            form_kwargs = {}
        form_kwargs = self.get_form_kwargs(item, **form_kwargs)
        return super(DotpathResource, self).get_create_schema_link(form_kwargs=form_kwargs, **kwargs)
    
    def get_create_link(self, item, form_kwargs=None, **kwargs):
        if form_kwargs is None:
            form_kwargs = {}
        form_kwargs = self.get_form_kwargs(item, **form_kwargs)
        return super(DotpathResource, self).get_create_link(form_kwargs, **kwargs)
    
    def get_item_prompt(self, item):
        return unicode(item.subobject)
    
    def get_resource_items(self):
        dotpath = self.state.dotpath
        item = self.state.parent
        if self.state.is_sublisting:
            instances = self.state.subobject
            if self.state.get('resource_class', None) == 'change_list':
                return [self.get_list_resource_item(item.instance, dotpath='%s.%s' % (dotpath, i)) for i in range(len(instances))]
            return [self.get_resource_item(item.instance, dotpath='%s.%s' % (dotpath, i)) for i in range(len(instances))]
        else:
            if self.state.get('resource_class', None) == 'change_list':
                return [self.get_list_resource_item(item.instance, dotpath=dotpath)]
            return [self.get_resource_item(item.instance, dotpath=dotpath)]
    
    def get_resource_subitem_class(self):
        return self.resource_subitem_class
    
    def get_resource_subitem(self, instance, **kwargs):
        kwargs.setdefault('endpoint', self)
        return self.get_resource_subitem_class()(instance=instance, **kwargs)
    
    def get_excludes(self):
        excludes = set()
        for field in self._get_complex_fields():
            excludes.add(field.name)
        return list(excludes)
    
    def get_list_resource_item_class(self):
        return self.get_resource_item_class()
    
    def get_form_class(self, dotpath=None, subobject=None):
        if self.state.dotpath:
            pass #TODO
        elif self.form_class:
            return self.form_class
        
        effective_dotpath = dotpath
        effective_schema = self.schema
        
        if effective_dotpath is None:
            effective_dotpath = self.state.dotpath
            
            if self.state.is_sublisting: #this means we are adding
                index = len(self.state.subobject)
                effective_dotpath = '%s.%s' % (effective_dotpath, index)
            elif subobject:
                effective_schema = type(subobject)
        
        class AdminForm(forms.DocumentForm):
            class Meta:
                document = self.document
                exclude = self.get_excludes()
                dotpath = effective_dotpath
                schema = effective_schema
                #TODO formfield overides
                #TODO fields
        return AdminForm
    
    def get_breadcrumbs(self):
        breadcrumbs = self.parent.get_breadcrumbs()
        parent_item = self.state.parent
        assert parent_item
        breadcrumbs.append(self.parent.get_item_breadcrumb(parent_item))
        #TODO fill all the dotpaths inbetween
        #TODO this part is funky...
        breadcrumbs.append(self.get_breadcrumb())
        return breadcrumbs
    
    def get_prompt(self):
        return self.schema._meta.module_name
    

class BaseDocumentResource(DocumentResourceMixin, CRUDResource):
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
    #changelist_class = DocumentChangeList
    dotpath_resource_class = DotpathResource
    
    #list display options
    list_per_page = 100
    list_max_show_all = 200
    
    def __init__(self, *args, **kwargs):
        super(BaseDocumentResource, self).__init__(*args, **kwargs)
        self.dotpath_resource = self.create_dotpath_resource()
    
    def create_dotpath_resource(self):
        cls = self.get_dotpath_resource_class()
        return cls(resource_adaptor=self.resource_adaptor, site=self.site, parent=self, api_request=self.api_request)
    
    def get_dotpath_resource_class(self):
        return self.dotpath_resource_class
    
    def get_view_endpoints(self):
        endpoints = super(CRUDResource, self).get_view_endpoints()
        endpoints.extend([
            (ListEndpoint, {}),
            (CreateEndpoint, {}),
            (DetailEndpoint, {}),
            (DeleteEndpoint, {}),
        ])
        return endpoints
    
    def get_extra_urls(self):
        urlpatterns = super(BaseDocumentResource, self).get_extra_urls()
        urlpatterns += patterns('',
            url(r'^(?P<pk>\w+)/dotpath/',
                include(self.dotpath_resource.urls)),
        )
        return urlpatterns
    
    def get_active_index(self, **kwargs):
        return self.get_queryset(user=self.state['auth'])
    
    def lookup_allowed(self, lookup, value):
        return True #TODO
    
    def get_excludes(self):
        excludes = set(self.exclude)
        for field in self._get_complex_fields():
            excludes.add(field.name)
        return list(excludes)
    
    def get_form_class(self):
        if self.form_class:
            return self.form_class
        class AdminForm(forms.DocumentForm):
            class Meta:
                document = self.document
                exclude = self.get_excludes()
                schema = self.schema
                #TODO formfield overides
                #TODO fields
        return AdminForm

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
        return '%s%s_' % (self.parent.get_base_url_name(), 'tempdoc')
    
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
                       'prompt':'commit',
                       'rel':'commit',}
        commit_link = Link(**link_kwargs)
        return commit_link
    
    def handle_commit_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            resource_item = self.get_resource_item(instance)
            return self.get_item_link(resource_item)
        return link.clone(form=form)

class DocumentResource(BaseDocumentResource):
    temporary_document_resource_class = TemporaryDocumentResource
    
    def __init__(self, *args, **kwargs):
        super(DocumentResource, self).__init__(*args, **kwargs)
        self.temporary_document_resource = self.create_temporary_document_resource()
    
    def create_temporary_document_resource(self):
        cls = self.get_temporary_document_resource_class()
        return cls(resource_adaptor=self.resource_adaptor, site=self.site, parent=self)
    
    def get_temporary_document_resource_class(self):
        return self.temporary_document_resource_class
    
    def get_extra_urls(self):
        urlpatterns = super(DocumentResource, self).get_extra_urls()
        urlpatterns += patterns('',
            url(r'^tempdoc/',
                include(self.temporary_document_resource.urls)),
        )
        return urlpatterns

