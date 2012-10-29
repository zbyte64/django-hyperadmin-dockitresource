from django.conf.urls.defaults import patterns, url, include

from hyperadmin.resources.crud.crud import CRUDResource
from hyperadmin.hyperobjects import Link

from dockit import forms
from dockit.schema.common import UnSet

from dockitresource import views
from dockitresource.changelist import DocumentChangeList, DotpathChangeList
from dockitresource.hyperobjects import DotpathState, DotpathNamespace, DotpathResourceItem, DotpathListResourceItem


class DocumentResourceMixin(object):
    state_class = DotpathState
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
    
    def get_view_kwargs(self):
        kwargs = super(DocumentResourceMixin, self).get_view_kwargs()
        kwargs['document'] = self.document
        return kwargs
    
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
                inline = self.dotpath_resource.fork_state(dotpath=dotpath, parent=item)
                subitem = inline.get_resource_item(item.instance, dotpath=dotpath)
                link = inline.get_item_link(subitem)
                namespace = DotpathNamespace(name=name, link=link, state=inline.state)
                namespaces[name] = namespace
            
        return namespaces
    
    def get_queryset(self, user):
        queryset = self.resource_adaptor.objects.all()
        if not self.has_change_permission(user):
            queryset = queryset.none()
        return queryset
    
    @property
    def schema_select(self):
        self.schema #TODO opperate off this instead?
        return self.state.get('schema_select', None) is not None
    
    def get_create_select_schema_form_class(self):
        from django import forms as djangoforms
        class SelectSchemaForm(djangoforms.Form):
            def __init__(self, **kwargs):
                self.instance = kwargs.pop('instance', None)
                super(SelectSchemaForm, self).__init__(**kwargs)
        
        typed_field = self.state['schema_select_field']
        key = self.schema._meta.typed_field
        SelectSchemaForm.base_fields[key] = djangoforms.ChoiceField(choices=typed_field.get_schema_choices())
        return SelectSchemaForm
    
    def get_create_schema_link(self, schema_type=None, form_kwargs=None, **kwargs):
        """
        Returns a link to the create view and includes a form for selecting the type of schema
        """
        if form_kwargs is None:
            form_kwargs = {}
        form_kwargs = self.get_form_kwargs(**form_kwargs)
        form_kwargs.setdefault('initial', {})
        if schema_type:
            form_kwargs['initial'][self.schema._meta.typed_field] = schema_type
            prompt = 'create %s' % schema_type
            link_factor = 'LO'
        else:
            prompt = 'create'
            link_factor = 'LT'
        
        link_kwargs = {'url':self.get_add_url(),
                       'resource':self,
                       'method':'GET',
                       'form_kwargs':form_kwargs,
                       'form_class': self.get_create_select_schema_form_class(),
                       'prompt':prompt,
                       'rel':'create',
                       'link_factor':link_factor,}
        link_kwargs.update(kwargs)
        create_link = Link(**link_kwargs)
        return create_link
    
    def get_typed_add_links(self, **kwargs):
        return [self.get_create_schema_link(**kwargs)]
        links = []
        for key, val in self.state['schema_select']:
            if key:
                links.append(self.get_create_schema_link(schema_type=key, **kwargs))
        return links
    
    def get_idempotent_links(self):
        links = super(CRUDResource, self).get_idempotent_links()
        if self.show_create_link() and not self.state.item: #only display a create link if we are not viewing a specific item
            if not self.schema_select:
                links.append(self.get_create_link())
        return links
    
    def get_outbound_links(self):
        links = super(CRUDResource, self).get_outbound_links()
        if self.show_create_link() and not self.state.item:
            if self.schema_select:
                links.extend(self.get_typed_add_links())
            else:
                links.append(self.get_create_link(link_factor='LO'))
        return links

class DotpathResource(DocumentResourceMixin, CRUDResource):
    changelist_class = DotpathChangeList
    resource_item_class = DotpathResourceItem
    list_resource_item_class = DotpathListResourceItem
    
    list_view = views.DotpathListView
    add_view = views.DotpathCreateView #TODO this is to append to a dotpath
    detail_view = views.DotpathDetailView #TODO this needs to double as a list view
    delete_view = views.DotpathDeleteView #TODO this needs to unlink the dotpath
    
    def get_base_url_name(self):
        return '%s%s_' % (self.parent.get_base_url_name(), 'dotpath')
    
    def get_urls(self):
        def wrap(view, cacheable=False):
            return self.as_view(view, cacheable)
        
        init = self.get_view_kwargs()
        
        # Admin-site-wide views.
        base_name = self.get_base_url_name()
        urlpatterns = self.get_extra_urls()
        urlpatterns += patterns('',
            url(r'^(?P<dotpath>[\w\.]+)/$',
                wrap(self.detail_view.as_view(**init)),
                name='%sdetail' % base_name),
            url(r'^(?P<dotpath>[\w\.]+)/add/$',
                wrap(self.add_view.as_view(**init)),
                name='%sadd' % base_name),
            url(r'^(?P<dotpath>[\w\.]+)/delete/$',
                wrap(self.delete_view.as_view(**init)),
                name='%sdelete' % base_name),
        )
        return urlpatterns
    
    def get_add_url(self):
        return self.reverse('%sadd' % self.get_base_url_name(), pk=self.state.parent.instance.pk, dotpath=self.state.dotpath)
    
    def get_delete_url(self, item):
        return self.reverse('%sdelete' % self.get_base_url_name(), pk=item.instance.pk, dotpath=item.dotpath or self.state.dotpath)
    
    def get_item_url(self, item):
        return self.reverse('%sdetail' % self.get_base_url_name(), pk=item.instance.pk, dotpath=item.dotpath or self.state.dotpath)
    
    def get_absolute_url(self):
        assert self.state.parent
        return self.reverse('%sdetail' % self.get_base_url_name(), pk=self.state.parent.instance.pk, dotpath=self.state.dotpath)
    
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
    
    def handle_create_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            resource_item = self.get_resource_item(instance, dotpath=form._meta.dotpath)
            return self.get_item_link(resource_item)
        return link.clone(form=form)
    
    def handle_update_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            resource_item = self.get_resource_item(instance, dotpath=self.state.dotpath)
            #or send the update link?
            return self.get_update_link(resource_item)
        return link.clone(form=form)
    
    def handle_delete_submission(self, link, submit_kwargs):
        instance = self.state.parent.instance
        instance.dot_notation_set_value(self.state.dotpath, UnSet)
        instance.save()
        return self.get_resource_link()
    
    def get_item_prompt(self, item):
        return unicode(item.subobject)
    
    def get_resource_items(self):
        dotpath = self.state.dotpath
        item = self.state.parent
        if self.state.is_sublisting:
            instances = self.state.subobject
            if self.state.get('view_class', None) == 'change_list':
                return [self.get_list_resource_item(item.instance, dotpath='%s.%s' % (dotpath, i)) for i in range(len(instances))]
            return [self.get_resource_item(item.instance, dotpath='%s.%s' % (dotpath, i)) for i in range(len(instances))]
        else:
            if self.state.get('view_class', None) == 'change_list':
                return [self.get_list_resource_item(item.instance, dotpath=dotpath)]
            return [self.get_resource_item(item.instance, dotpath=dotpath)]
        
    
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
        
        if effective_dotpath is None:
            effective_dotpath = self.state.dotpath
            
            if self.state.is_sublisting: #this means we are adding
                index = len(self.state.subobject)
                effective_dotpath = '%s.%s' % (effective_dotpath, index)
        
        effective_schema = self.schema
        if subobject:
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
    
    def show_create_link(self):
        return not self.state.has_view_class('change_form') and (not self.state.item or self.state.is_sublisting)
    
    def show_delete_link(self, item):
        return super(DotpathResource, self).show_delete_link(item) and not self.state.has_view_class('add_form')
    
    def get_idempotent_links(self):
        links = super(CRUDResource, self).get_idempotent_links()
        if self.show_create_link() and not self.state.item: #only display a create link if we are not viewing a specific item
            if not self.schema_select:
                links.append(self.get_create_link(item=self.state.parent))
        return links
    
    def get_outbound_links(self):
        links = super(CRUDResource, self).get_outbound_links()
        if self.show_create_link() and not self.state.item:
            if self.schema_select:
                links.extend(self.get_typed_add_links(item=self.state.parent, link_factor='LO', include_form_params_in_url=True))
            else:
                links.append(self.get_create_link(item=self.state.parent, link_factor='LO'))
        return links
    
    def get_breadcrumbs(self):
        breadcrumbs = self.parent.get_breadcrumbs()
        parent_item = self.state.parent
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
    changelist_class = DocumentChangeList
    dotpath_resource_class = DotpathResource
    
    #list display options
    list_per_page = 100
    list_max_show_all = 200
    
    list_view = views.DocumentListView
    add_view = views.DocumentCreateView
    detail_view = views.DocumentDetailView
    delete_view = views.DocumentDeleteView
    
    def __init__(self, *args, **kwargs):
        super(BaseDocumentResource, self).__init__(*args, **kwargs)
        self.dotpath_resource = self.create_dotpath_resource()
    
    def create_dotpath_resource(self):
        cls = self.get_dotpath_resource_class()
        return cls(resource_adaptor=self.resource_adaptor, site=self.site, parent_resource=self)
    
    def get_dotpath_resource_class(self):
        return self.dotpath_resource_class
    
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
        return cls(resource_adaptor=self.resource_adaptor, site=self.site, parent_resource=self)
    
    def get_temporary_document_resource_class(self):
        return self.temporary_document_resource_class
    
    def get_extra_urls(self):
        urlpatterns = super(DocumentResource, self).get_extra_urls()
        urlpatterns += patterns('',
            url(r'^tempdoc/',
                include(self.temporary_document_resource.urls)),
        )
        return urlpatterns

