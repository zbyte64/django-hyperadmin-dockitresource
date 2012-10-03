from hyperadmin.hyperobjects import State, Namespace

class DotpathState(State):
    def set_dotpath(self, val):
        self.params['_dopath'] = val
    
    def get_dotpath(self):
        return self.params.get('_dotpath', '')
    
    dotpath = property(get_dotpath, set_dotpath)
    
    def get_query_string(self, new_params=None, remove=None):
        if new_params and 'dotpath' in new_params:
            val = new_params.pop('dotpath')
            new_params['_dotpath'] = val
        if remove and 'dotpath' in remove:
            remove = list(remove)
            remove.remove('dotpath')
            remove.append('_dotpath')
        return super(DotpathState, self).get_query_string(new_params=new_params, remove=remove)

class DotpathNamespace(Namespace):
    pass
