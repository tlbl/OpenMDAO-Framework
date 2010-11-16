# pylint: disable-msg=C0111,C0103

import os.path
import sys
import unittest
import StringIO
import nose
import copy

from enthought.traits.api import TraitError, HasTraits, TraitType

import openmdao.util.eggsaver as constants
from openmdao.main.container import Container, get_default_name, \
                                    deep_hasattr, get_default_name, find_name, \
                                    find_trait_and_value, _get_entry_group, \
                                    create_io_traits
from openmdao.lib.datatypes.api import Float, Int, Bool, List, Dict, TraitError
from openmdao.util.testutil import make_protected_dir

# Various Pickle issues arise only when this test runs as the main module.
# This is used to detect when we're the main module or not.
MODULE_NAME = __name__

class DumbTrait(TraitType):
    def validate(self, obj, name, value):
        """Validation for the PassThroughTrait"""
        if self.validation_trait:
            return self.validation_trait.validate(obj, name, value)
        return value

class MyContainer(Container):
    def __init__(self, *args, **kwargs):
        super(MyContainer, self).__init__(*args, **kwargs)
        self.add_trait('dyntrait', Float(9., desc='some desc'))


class MyBuilderContainer(Container):
    def build_trait(self, ref_name, iotype=None, trait=None):
        if iotype is None:
            iostat = 'in'
        else:
            iostat = iotype
            
        if trait is None:
            if ref_name.startswith('f'):
                trait = Float(0.0, iotype=iostat, ref_name=ref_name)
            elif ref_name.startswith('i'):
                trait = Int(0, iotype=iostat, ref_name=ref_name)
            else:
                self.raise_exception("can't determine type of variable '%s'"
                                         % ref_name, RuntimeError)
        return trait
    
    
class ContainerTestCase(unittest.TestCase):

    def setUp(self):
        """This sets up the following hierarchy of Containers:
        
                       root
                       /  \
                     c1    c2
                          /  \
                        c21  c22
                             /
                          c221
                          /
                        number
        """
        
        self.root = Container()
        self.root.add('c1', Container())
        self.root.add('c2', Container())
        self.root.c2.add('c21', Container())
        self.root.c2.add('c22', Container())
        self.root.c2.c22.add('c221', Container())
        self.root.c2.c22.c221.add_trait('number', Float(3.14, iotype='in'))

    def tearDown(self):
        """this teardown function will be called after each test"""
        self.root = None

    def test_deepcopy(self):
        cont = MyContainer()
        self.assertEqual(cont.dyntrait, 9.)
        ccont = copy.deepcopy(cont)
        self.assertEqual(ccont.dyntrait, 9.)
        cont.dyntrait = 12.
        ccont2 = copy.deepcopy(cont)
        self.assertEqual(ccont2.dyntrait, 12.)
        
    def test_build_trait(self):
        mbc = MyBuilderContainer()
        obj_info = ['f_in', ('f_out', 'f_out_internal', 'out'),
                    'i_in', 'i_out',
                    ('b_out', 'b_out_internal', 'out', Bool())
            ]
        create_io_traits(mbc, obj_info)
        create_io_traits(mbc, 'foobar')
        self.assertTrue(mbc.get_trait('b_out').is_trait_type(Bool))
        self.assertTrue(mbc.get_trait('f_out').is_trait_type(Float))
        self.assertEqual(mbc.get_trait('f_out').iotype, 'out')
        self.assertTrue(mbc.get_trait('i_in').is_trait_type(Int))
        self.assertEqual(mbc.get_trait('f_in').iotype, 'in')
        self.assertTrue(mbc.get_trait('foobar').is_trait_type(Float))
        self.assertEqual(mbc.get_trait('foobar').iotype, 'in')

        
    def test_connect(self):
        cont = MyContainer()
        cont.connect('parent.foo', 'dyntrait')
        self.assertEqual(cont._depgraph.get_source('dyntrait'), 'parent.foo')
        
        cont.disconnect('parent.foo', 'dyntrait')
        self.assertEqual(cont._depgraph.get_source('dyntrait'), None)
        
    def test_find_trait_and_value(self):
        class MyClass(object):
            pass
        class MyHT(HasTraits):
            pass
        
        obj = MyClass()
        obj.sub = MyClass()
        obj.sub.sub = MyHT()
        obj.sub.csub = Container()
        obj.a = 1
        obj.sub.b = 2
        obj.sub.sub.c = 3
        obj.sub.csub.add_trait('d',Float(4, iotype='in'))
        result = find_trait_and_value(obj, 'sub.sub.c')
        self.assertEqual(result[0].type, 'python')
        self.assertEqual(result[1], 3)
        result = find_trait_and_value(obj, 'sub.csub.d')
        self.assertEqual(result[0].type, 'trait')
        self.assertEqual(result[1], 4)
        try:
            result = find_trait_and_value(obj, 'sub.foo')
        except AttributeError as err:
            self.assertEqual(str(err), "'MyClass' object has no attribute 'foo'")
        else:
            self.fail("expected AttributeError")
        
    def test_deep_hasattr(self):
        class MyClass(object):
            pass
        obj = MyClass()
        obj.sub = MyClass()
        obj.sub.sub = MyClass()
        obj.a = 1
        obj.sub.b = 2
        obj.sub.sub.c = 3
        self.assertEqual(deep_hasattr(obj,'a'), True)
        self.assertEqual(deep_hasattr(obj,'z'), False)
        self.assertEqual(deep_hasattr(obj,'sub'), True)
        self.assertEqual(deep_hasattr(obj,'bus'), False)
        self.assertEqual(deep_hasattr(obj,'sub.b'), True)
        self.assertEqual(deep_hasattr(obj,'sub.y'), False)
        self.assertEqual(deep_hasattr(obj,'sub.sub.c'), True)
        self.assertEqual(deep_hasattr(obj,'sub.sub.d'), False)
        self.assertEqual(deep_hasattr(obj,'sub.blah.foo.d'), False)
        
    def test_get_default_name(self):
        class MyClass(object):
            pass
        parent = MyClass()
        pname = get_default_name(parent, None)
        self.assertEqual(pname, 'myclass1')
        
        for i in range(3):
            obj = MyClass()
            oname = get_default_name(obj, parent)
            setattr(parent, oname, obj)
            self.assertEqual(oname, "myclass%s" % (i+1))
            
    def test_find_name(self):
        class MyClass(object):
            pass
        obj = MyClass()
        obj2 = MyClass()
        self.assertEqual(find_name(obj, obj2), '')
        setattr(obj, 'foo', obj2)
        self.assertEqual(find_name(obj, obj2), 'foo')
        
    def test_get_entry_group(self):
        class MyClass(object):
            pass
        self.assertEqual(_get_entry_group(MyClass()), None)
        self.assertEqual(_get_entry_group(Container()), 'openmdao.container')


    def test_add_bad_child(self):
        foo = Container()
        try:
            foo.add('non_container', 'some string')
        except TypeError, err:
            self.assertEqual(str(err), ": '<type 'str'>' "+
                "object is not an instance of Container.")
        else:
            self.fail('TypeError expected')
        
    def test_pathname(self):
        self.root.add('foo', Container())
        self.root.foo.add('foochild', Container())
        self.assertEqual(self.root.foo.foochild.get_pathname(), 'foo.foochild')

    def test_get(self):
        obj = self.root.get('c2.c21')
        self.assertEqual(obj.get_pathname(), 'c2.c21')
        num = self.root.get('c2.c22.c221.number')
        self.assertEqual(num, 3.14)

    def test_add_trait_w_subtrait(self):
        obj = Container()
        obj.add_trait('lst', List([1,2,3], iotype='in'))
        obj.add_trait('dct', Dict({}, iotype='in'))

    def test_get_attribute(self):
        self.assertEqual(self.root.get('c2.c22.c221').get_trait('number').iotype, 
                         'in')
        
    def test_full_items(self):
        lst = map(lambda x: x[0], self.root.items(recurse=True))
        self.assertEqual(lst,
            ['c2', 'c2.c22', 'c2.c22.c221', 'c2.c22.c221.number', 'c2.c21', 'c1'])
        
        items = [(x[0],isinstance(x[1],Container) or str(x[1])) 
                    for x in self.root.items(recurse=True)]
        
        # values of True in the list below just indicate that the value
        # is a Container
        self.assertEqual(items, [('c2', True), 
                                 ('c2.c22', True), 
                                 ('c2.c22.c221', True), 
                                 ('c2.c22.c221.number', '3.14'), 
                                 ('c2.c21', True), 
                                 ('c1', True)])
        
    def test_default_naming(self):
        cont = Container()
        cont.add('container1', Container())
        cont.add('container2', Container())
        self.assertEqual(get_default_name(Container(), cont), 'container3')
        self.assertEqual(get_default_name(Container(), None), 'container1')
        
    def test_bad_get(self):
        try:
            x = self.root.bogus
        except AttributeError, err:
            self.assertEqual(str(err),"'Container' object has no attribute 'bogus'")
        else:
            self.fail('AttributeError expected')

    def test_iteration(self):
        names = [x.get_pathname() for n,x in self.root.items(recurse=True)
                                         if isinstance(x, Container)]
        self.assertEqual(set(names),
                         set(['c1', 'c2', 'c2.c21', 
                              'c2.c22', 'c2.c22.c221']))
        
        names = [x.get_pathname() for n,x in self.root.items()
                                         if isinstance(x, Container)]
        self.assertEqual(set(names), set(['c1', 'c2']))
        
        names = [x.get_pathname() for n,x in self.root.items(recurse=True)
                                 if isinstance(x, Container) and x.parent==self.root]
        self.assertEqual(set(names), set(['c1', 'c2']))

        names = [x.get_pathname() for n,x in self.root.items(recurse=True)
                                 if isinstance(x, Container) and x.parent==self.root.c2]
        self.assertEqual(set(names), set(['c2.c21', 'c2.c22']))

    # TODO: all of these save/load test functions need to do more checking
    #       to verify that the loaded thing is equivalent to the saved thing
    
    def test_save_load_yaml(self):
        output = StringIO.StringIO()
        c1 = Container()
        c1.add('c2', Container())
        c1.save(output, constants.SAVE_YAML)
        
        inp = StringIO.StringIO(output.getvalue())
        newc1 = Container.load(inp, constants.SAVE_YAML)
                
    def test_save_load_libyaml(self):
        output = StringIO.StringIO()
        c1 = Container()
        c1.add('c2', Container())
        c1.save(output, constants.SAVE_LIBYAML)
        
        inp = StringIO.StringIO(output.getvalue())
        newc1 = Container.load(inp, constants.SAVE_LIBYAML)
                
    def test_save_load_cpickle(self):
        output = StringIO.StringIO()
        c1 = Container()
        c1.add('c2', Container())
        c1.save(output)
        
        inp = StringIO.StringIO(output.getvalue())
        newc1 = Container.load(inp)
        
    def test_save_load_pickle(self):
        output = StringIO.StringIO()
        c1 = Container()
        c1.add('c2', Container())
        c1.save(output, constants.SAVE_PICKLE)
        
        inp = StringIO.StringIO(output.getvalue())
        newc1 = Container.load(inp, constants.SAVE_PICKLE)
                
    def test_save_bad_format(self):
        output = StringIO.StringIO()
        c1 = Container()
        try:
            c1.save(output, 'no-such-format')
        except RuntimeError, exc:
            msg = ": Can't save object using format 'no-such-format'"
            self.assertEqual(str(exc), msg)
        else:
            self.fail('Expected RuntimeError')

    def test_save_bad_filename(self):
# TODO: get make_protected_dir() to work on Windows.
        if sys.platform == 'win32':
            raise nose.SkipTest()

        c1 = Container()
        directory = make_protected_dir()
        path = os.path.join(directory, 'illegal')
        try:
            c1.save(path)
        except IOError, exc:
            msg = ": Can't save to '%s': Permission denied" % path
            self.assertEqual(str(exc), msg)
        else:
            self.fail('Expected IOError')
        finally:
            os.rmdir(directory)

    def test_save_bad_method(self):
        # This test exercises handling references to unbound methods defined
        # in __main__.  Because of this, it only does it's job if this is the
        # main module (not run as part of a larger suite in the buildout dir).
        output = StringIO.StringIO()
        c1 = Container()
        c1.unbound_thing = ContainerTestCase.test_save_bad_method
        try:
            c1.save(output)
        except RuntimeError, exc:
            msg = ": _pickle_method: <unbound method ContainerTestCase" \
                  ".test_save_bad_method> with module __main__ (None)"
            self.assertEqual(str(exc), msg)
        else:
            if MODULE_NAME == '__main__':
                self.fail('Expected RuntimeError')

    def test_load_bad_format(self):
        try:
            Container.load(StringIO.StringIO(''), 'no-such-format')
        except RuntimeError, exc:
            msg = "Can't load object using format 'no-such-format'"
            self.assertEqual(str(exc), msg)
        else:
            self.fail('Expected RuntimeError')

    def test_load_nofile(self):
        try:
            Container.load('no-such-file')
        except ValueError, exc:
            msg = "Bad state filename 'no-such-file'."
            self.assertEqual(str(exc), msg)
        else:
            self.fail('Expected ValueError')
            

if __name__ == "__main__":
    import nose
    import sys
    sys.argv.append('--cover-package=openmdao')
    sys.argv.append('--cover-erase')
    nose.runmodule()

