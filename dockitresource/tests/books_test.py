from hyperadmin.tests.test_resources import ResourceTestCase

from django.http import Http404

from dockitresource.resources import DocumentResource
from dockitresource.tests.books_models import Book, Publisher, Author, Address

##resource defs##

class BookResource(DocumentResource):
    list_display = ('title', 'authors_list', 'publisher', 'year')

    def authors_list(self, obj):
        return ', '.join([unicode(author) for author in obj.authors])

class PublisherResource(DocumentResource):
    list_display = ('name', 'city_and_region')

    def city_and_region(self, obj):
        return obj.address.city + ', ' + obj.address.region

class AuthorResource(DocumentResource):
    list_display = ('internal_id', 'user')

class ComplexObjectResource(DocumentResource):
    pass


##test defs##

class BookTestCase(ResourceTestCase):
    def setUp(self):
        super(BookTestCase, self).setUp()
        self.setup_fixtures()
    
    def setup_fixtures(self):
        user = self.user
        addr = Address(street_1='10533 Reagan Rd', city='San Diego', postal_code='92126', country='US', region='CA')

        author = Author(user=user)
        author.save()

        publisher = Publisher(name='Books etc', address=addr)
        publisher.save()

        book = Book(title='Of Mice and Men', publisher=publisher)
        book.authors.append(author)
        book.save()
        book.tags.append('historical')
        book.save()
    
    def register_resource(self):
        self.site.register(Book, BookResource)
        return self.site.registry[Book]
    
    def test_get_list(self):
        api_request = self.get_api_request()
        endpoint = self.resource.endpoints['list'].fork(api_request=api_request)
        response = endpoint.dispatch_api(api_request)
        
        call_kwargs = api_request.generate_response.call_args[1]
        link = call_kwargs['link']
        state = call_kwargs['state']
        
        self.assertEqual(len(state.get_resource_items()), Book.objects.count())
        
        #links = state.links.get_filter_links()
        #self.assertTrue(links, 'filter links are empty')
        
        links = state.links.get_breadcrumbs()
        self.assertTrue(links, 'breadcrumbs are empty')
        
        links = state.links.get_outbound_links()
        self.assertTrue(links, 'outbound links are empty')
    
    def test_get_detail(self):
        instance = Book.objects.all()[0]
        api_request = self.get_api_request(url_kwargs={'pk':instance.pk})
        endpoint = self.resource.endpoints['detail'].fork(api_request=api_request)
        response = endpoint.dispatch_api(api_request)
        
        call_kwargs = api_request.generate_response.call_args[1]
        link = call_kwargs['link']
        state = call_kwargs['state']
        
        self.assertEqual(len(state.get_resource_items()), 1)
        self.assertTrue(state.item)
        self.assertEqual(state.item.instance, instance)
        
        links = state.links.get_breadcrumbs()
        #TODO check for item breadcrumb
        self.assertTrue(links, 'breadcrumbs are empty')
        
        links = state.item.links.get_item_outbound_links()
        self.assertTrue(links, 'outbound links are empty')
    
    def test_get_detail_404(self):
        instance = Book.objects.all()[0]
        api_request = self.get_api_request(url_kwargs={'pk':'0'})
        endpoint = self.resource.endpoints['detail'].fork(api_request=api_request)
        try:
            response = endpoint.dispatch_api(api_request)
        except Http404:
            pass
        else:
            self.fail("Did not return 404 for non-existant object")
    
    def test_post_list(self):
        update_data = {
            'title': 'Big Title',
        }
        api_request = self.get_api_request(payload={'data': update_data}, method='POST')
        endpoint = self.resource.endpoints['list'].fork(api_request=api_request)
        
        response = endpoint.dispatch_api(api_request)
        
        call_kwargs = api_request.generate_response.call_args[1]
        link = call_kwargs['link']
        state = call_kwargs['state']
        
        self.assertTrue(link.form)
        self.assertTrue(link.form.errors)
    
    def test_post_detail(self):
        instance = Book.objects.all()[0]
        update_data = {
            'title': 'Big Title',
        }
        api_request = self.get_api_request(url_kwargs={'pk':instance.pk}, payload={'data': update_data}, method='POST')
        endpoint = self.resource.endpoints['detail'].fork(api_request=api_request)
        response = endpoint.dispatch_api(api_request)
        
        call_kwargs = api_request.generate_response.call_args[1]
        link = call_kwargs['link']
        state = call_kwargs['state']
        
        #with state.push_session(self.popped_states):
        self.assertTrue(link.form)
        self.assertTrue(link.form.errors)
        
        self.assertTrue(state.item)
        self.assertEqual(state.item.instance, instance)

'''
class PolymorphismTestCase(unittest.TestCase):
    def test_polymorphism_preserves_collection(self):
        self.assertEqual(Newspaper._meta.collection, Publication._meta.collection)
        self.assertEqual(Magazine._meta.collection, Publication._meta.collection)
    
    def test_poymorphism_save(self):
        paper = Newspaper(name='UT', city='San Diego')
        paper.save()
        self.assertEqual(paper._type, Newspaper._meta.typed_key)
        
        mag = Magazine(name='SO', issue_number='50')
        mag.save()
        self.assertEqual(mag._type, Magazine._meta.typed_key)
        
        self.assertEqual(len(Publication.objects.all()), 2)
        
        for obj in Publication.objects.all():
            if obj.name == 'SO':
                self.assertEqual(obj._type, Magazine._meta.typed_key)
                self.assertTrue(isinstance(obj, Magazine))
            if obj.name == 'UT':
                self.assertEqual(obj._type, Newspaper._meta.typed_key)
                self.assertTrue(isinstance(obj, Newspaper))
    
    def test_nested_polymorphism(self):
        brand = Brand(name='foobur')
        brand.products.append(Shoes(name='shoes'))
        brand.products.append(Shirt(name='shirt'))
        brand.save()
        
        brand = Brand.objects.get(pk=brand.pk)
        self.assertTrue(isinstance(brand.products[0], Shoes))
        
        shirt = brand.dot_notation_to_value('products.1')
        self.assertTrue(isinstance(shirt, Shirt))
        
'''
