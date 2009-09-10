
#public symbols
__all__ = ['Component', 'SimulationRoot']



import fnmatch
import glob
import logging
import os.path
import pkg_resources
import shutil
import subprocess
import sys
import time
import StringIO

from enthought.traits.api import implements, on_trait_change, Str, Missing, \
                                 Undefined, Python, TraitError
from enthought.traits.trait_base import not_event

from openmdao.main.container import Container, set_as_top
from openmdao.main.filevar import FileValue
from openmdao.util.eggsaver import SAVE_CPICKLE
from openmdao.main.log import LOG_DEBUG

# Execution states.
STATE_UNKNOWN = -1
STATE_IDLE    = 0
STATE_RUNNING = 1
STATE_WAITING = 2


class SimulationRoot (object):
    """Singleton object used to hold root directory."""

    # Execution root directory. Root of all legal file paths.
    __root = None

    @staticmethod
    def chdir (path):
        """Change to directory 'path' and set the singleton's root.
        Normally not called, but useful in special situations."""
        os.chdir(path)
        SimulationRoot.__root = os.getcwd()

    @staticmethod
    def get_root ():
        """Return this simulation's root directory path."""
        if SimulationRoot.__root is None:
            SimulationRoot.__root = os.getcwd()
        return SimulationRoot.__root

    @staticmethod
    def legal_path (path):
        """Return True if path is legal (decendant of our root)."""
        if SimulationRoot.__root is None:
            SimulationRoot.__root = os.getcwd()
        return path.startswith(SimulationRoot.__root)
    
def _relpath(path1, path2):
    """Return path for path1 relative to path2."""
    assert os.path.isabs(path1)
    assert os.path.isabs(path2)

    if path1.endswith(os.sep):
        path = path1[:-1]
    else:
        path = path1
    if path2.endswith(os.sep):
        start = path2[:-1]
    else:
        start = path2

    if path == start:
        return ''

    relpath = ''
    while start:
        if path.startswith(start):
            return os.path.join(relpath, path[len(start)+1:])
        relpath = os.path.join('..', relpath)
        start = os.path.dirname(start)

class Component (Container):
    """This is the base class for all objects containing Traits that are 
       accessible to the OpenMDAO framework and are 'runnable'.

    - `directory` is a string specifying the directory to execute in. \
       If it is a relative path, it is relative to its parent's directory.
    - `external_files` is a list of meta-data dictionaries for external \
      files used by the component.  The 'path' meta-data attribute can be \
      a glob-style pattern.
    """

    directory = Str('',desc='If non-blank, the directory to execute in.', 
                    iostatus='in')
    state = Python
    external_files = Python
        
    def __init__(self, doc=None, directory=''):
        super(Component, self).__init__(doc)
        
        self.state = STATE_IDLE
        self._stop = False
        self._call_check_config = True
        self._call_execute = True
        if directory:
            self.directory = directory
        
        self._dir_stack = []
        
        # List of meta-data dictionaries.
        self.external_files = []

    #def _directory_changed(self, old, new):
        #if not self._call_tree_defined:
            #self.check_path(self.get_abs_directory(), 
                            #check_exist=True)
            
    def check_config (self):
        """Verify that this component is fully configured to execute.
        This function is called once prior to the first execution of this
        component, and may be called explicitly at other times if desired. 
        Classes that override this function must still call the base class
        version.
        """
        self._call_check_config = False
    
    def tree_defined(self):
        """Called after the hierarchy containing this Container has been
        defined back to the root. This does not guarantee that all sibling
        Containers have been defined. It also does not guarantee that this
        component is fully configured to execute. Classes that override this
        function must still call the base class version.
        """
        super(Component, self).tree_defined()
        if self.directory:
            path = self.get_abs_directory()
            if not os.path.exists(path):
                self.check_path(path) # make sure it's legal path before creating
                try:
                    os.makedirs(path)
                except OSError, exc:
                    self.raise_exception(
                        "Can't create execution directory '%s': %s"
                        % (path, exc.strerror), OSError)
            else:
                self.check_path(path, check_exist=True)
        
    def _pre_execute (self):
        """Make preparations for execution. Overrides of this function must
        call this version.
        """
        if self._call_tree_defined:
            self.tree_defined()
            
        if self._call_check_config:
            self.check_config()
        
        if self.parent is None: # if parent is None, we're not part of an Assembly
                                # so Variable validity doesn't apply. Just execute.
            self._call_execute = True
        else:
            invalid_ins = self.list_inputs(valid=False)
            if len(invalid_ins) > 0:
                #self.debug('updating inputs %s on %s' % (invalid_ins,self.get_pathname()))
                self._call_execute = True
                name = self.name
                if hasattr(self.parent, 'update_inputs'):
                    self.parent.update_inputs(name,
                                              ['.'.join([name, n]) for n in invalid_ins])
    
                            
    def execute (self):
        """Perform calculations or other actions, assuming that inputs 
        have already been set. This should be overridden in derived classes.
        """
        pass
    
    def _post_execute (self):
        """Update output variables and anything else needed after execution. 
        Overrides of this function must call this version.
        """
        # make our Variables valid again
        for name in self.list_inputs():
            self.set_valid(name, True)
        for name in self.list_outputs():
            self.set_valid(name, True)
        self._call_execute = False
        
    def run (self, force=False):
        """Run this object. This should include fetching input variables,
        executing, and updating output variables. Do not override this function.
        """
        if self.directory:
            directory = self.get_abs_directory()
            try:
                self.push_dir(directory)
            except OSError, exc:
                msg = "Could not move to execution directory '%s': %s" % \
                      (directory, exc.strerror)
                self.raise_exception(msg, RuntimeError)

        self.state = STATE_RUNNING
        self._stop = False
        try:
            self._pre_execute()
            if self._call_execute or force:
                #if __debug__: self._logger.debug('execute %s' % self.get_pathname())
                self.execute()
                self._post_execute()
        finally:
            self.state = STATE_IDLE
            if self.directory:
                self.pop_dir()
 
    def add_container(self, name, obj):
        """Override of base class version to force call to check_config after
        any child containers are added.
        Returns the added Container object.
        """
        self._call_check_config = True # force config check prior to next execution
        return super(Component, self).add_container(name, obj)
        
    def remove_container(self, name):
        """Override of base class version to force call to check_config after
        any child containers are removed.
        """
        self._call_check_config = True # force config check prior to next execution
        super(Component, self).remove_container(name)

    def add_trait(self, name, *trait):
        """Overrides base definition of add_trait in order to
        force call to check_config prior to execution when new traits are
        added.
        """
        self._call_check_config = True # force config check prior to next execution
        super(Component, self).add_trait(name, *trait)
        
    def remove_trait(self, name):
        """Overrides base definition of add_trait in order to
        force call to check_config prior to execution when a trait is
        removed.
        """
        self._call_check_config = True # force config check prior to next execution
        super(Component, self).remove_trait(name)    

    def check_path(self, path, check_exist=False):
        """Verify that the given path is a directory and is located
        within the allowed area (somewhere within the simulation root path).
        """
# pylint: disable-msg=E1101
        if not SimulationRoot.legal_path(path):
            self.raise_exception(
                "Illegal execution directory '%s', not a decendant of '%s'."
                % (path, SimulationRoot.get_root()),
                ValueError)
        elif not os.path.isdir(path) and check_exist:
                self.raise_exception(
                    "Execution directory path '%s' is not a directory."
                    % path, ValueError)
# pylint: enable-msg=E1101
        return path
    
    def get_abs_directory (self):
        """Return absolute path of execution directory."""
        path = self.directory
        if not os.path.isabs(path):
            if self._call_tree_defined:
                self.raise_exception("can't call get_abs_directory before hierarchy is defined",
                                     RuntimeError)
            if self.parent is not None and isinstance(self.parent, Component):
                parent_dir = self.parent.get_abs_directory()
            else:
                parent_dir = SimulationRoot.get_root()
            path = os.path.join(parent_dir, path)
            
        return path

    def push_dir (self, directory):
        """Change directory to dir, remembering current for later pop_dir()."""
        if not directory:
            directory = '.'
        cwd = os.getcwd()
        if not os.path.isabs(directory):
            directory = os.path.join(self.get_abs_directory(), directory)
        if not SimulationRoot.legal_path(directory):
            self.raise_exception(
                "Illegal directory '%s', not a decendant of '%s'." % \
                (directory, SimulationRoot.get_root()), ValueError)
        os.chdir(directory)
        self._dir_stack.append(cwd)

    def pop_dir (self):
        """Return to previous directory saved by push_dir()."""
        os.chdir(self._dir_stack.pop())

    def checkpoint (self, outstream, format=SAVE_CPICKLE):
        """Save sufficient information for a restart. By default, this
        just calls save().
        """
        self.save(outstream, format)

    def restart (self, instream):
        """Restore state using a checkpoint file. The checkpoint file is
        typically a delta from a full saved state file. If checkpoint is
        overridden, this should also be overridden.
        """
        self.load(instream)

    def save_to_egg(self, name=None, version=None, py_dir=None,
                    force_relative=True, src_dir=None, src_files=None,
                    child_objs=None, dst_dir=None, format=SAVE_CPICKLE,
                    proto=-1, use_setuptools=False):
        """Save state and other files to an egg.  Typically used to copy all or
        part of a simulation to another user or machine.  By specifying child
        components in `child_objs`, it will be possible to create instances of
        just those components from the installed egg.  Child component names
        should be specified relative to this component.

        - `name` defaults to the name of the component.
        - `version` defaults to the container's module __version__, or \
          a timestamp if no __version__ exists.
        - `py_dir` is the (root) directory for local Python files. \
          It defaults to the current directory.
        - If `force_relative` is True, all paths are made relative to `src_dir`.
        - `src_dir` is the root of all (relative) `src_files`. \
          It defaults to the component's directory.
        - `src_files` should be a set. Component external files will be added \
          to this set.
        - `child_objs` is a list of child objects for additional entries.
        - `dst_dir` is the directory to write the egg in.

        The resulting egg can be unpacked on UNIX via 'sh egg-file'.
        Returns (egg_filename, required_distributions, orphan_modules).
        """
        if src_dir is None:
            src_dir = self.get_abs_directory()
        if src_dir.endswith(os.sep):
            src_dir = src_dir[:-1]
        if src_files is None:
            src_files = set()

        fixup_dirs = []  # Used to restore original component config.
        fixup_meta = []
        fixup_fvar = []

        # Process all components in bottom-up order.
        # We have to check relative paths like '../somedir' and if
        # we do that after adjusting a parent, things can go bad.
        components = [self]
        components.extend([c for c in self.values(recurse=True)
                                if isinstance(c, Component)])
        for comp in sorted(components, reverse=True,
                           key=lambda comp: comp.get_pathname()):

            # Process execution directory.
            comp_dir = comp.get_abs_directory()
            if force_relative:
                if comp_dir.startswith(src_dir):
                    if comp_dir == src_dir and comp.directory:
                        fixup_dirs.append((comp, comp.directory))
                        comp.directory = ''
                    elif os.path.isabs(comp.directory):
                        parent_dir = comp.parent.get_abs_directory()
                        fixup_dirs.append((comp, comp.directory))
                        comp.directory = self._relpath(comp_dir, parent_dir)
                    logging.debug("%s.directory reset to '%s'" % 
                                  (comp.name,comp.directory))
                else:
                    self.raise_exception(
                        "Can't save, %s directory '%s' doesn't start with '%s'."
                        % (comp.get_pathname(), comp_dir, src_dir), ValueError)

            # Process external files.
            for metadata in comp.external_files:
                path = metadata['path']
                path = os.path.expanduser(path)
                path = os.path.expandvars(path)
                if not os.path.isabs(path):
                    path = os.path.join(comp_dir, path)
                paths = glob.glob(path)
                for path in paths:
                    path = os.path.normpath(path)
                    if not os.path.exists(path):
                        continue
                    if force_relative:
                        if path.startswith(src_dir):
                            save_path = self._relpath(path, src_dir)
                            if os.path.isabs(metadata['path']):
                                path = self._relpath(path, comp_dir)
                                fixup_meta.append((metadata, metadata['path']))
                                metadata['path'] = path
                        else:
                            self.raise_exception(
                                "Can't save, %s file '%s' doesn't start with '%s'."
                                % (comp.get_pathname(), path, src_dir),
                                ValueError)
                    else:
                        save_path = path
                    src_files.add(save_path)

            # Process FileTraits for this component only.
            for fvarname, fvar, ftrait in comp.get_file_vars():
                path = fvar.filename
                if not path:
                    continue
                if not os.path.isabs(path):
                    path = os.path.join(comp_dir, path)
                path = os.path.normpath(path)
                if not os.path.exists(path):
                    continue
                if force_relative:
                    if path.startswith(src_dir):
                        save_path = self._relpath(path, src_dir)
                        if os.path.isabs(fvar.filename):
                            path = self._relpath(path, comp_dir)
                            fixup_fvar.append((comp, fvarname, fvar))
                            comp.set(fvarname+'.filename', path, force=True)
                    else:
                        self.raise_exception(
                            "Can't save, %s path '%s' doesn't start with '%s'."
                            % ('.'.join([comp.get_pathname(),
                                         fvarname]), path, src_dir), ValueError)
                else:
                    save_path = path
                src_files.add(save_path)
        # Save relative directory for any entry points. Some oddness with
        # parent weakrefs seems to prevent reconstruction in load().
        if child_objs is not None:
            for child in child_objs:
                if not isinstance(child, Component):
                    continue
                relpath = child.directory
                obj = child.parent
                if obj is None:
                    raise RuntimeError('Entry point object has no parent!')
                while obj.parent is not None and \
                      isinstance(obj.parent, Component):
                    relpath = os.path.join(obj.directory, relpath)
                    obj = obj.parent
                child._rel_dir_path = relpath

        try:
            return super(Component, self).save_to_egg(
                       name, version, py_dir, src_dir, src_files,
                       child_objs, dst_dir, format, proto, use_setuptools)
        finally:
            # If any component config has been modified, restore it.
            for ccomp, path in fixup_dirs:
                ccomp.directory = path
            for meta, path in fixup_meta:
                meta['path'] = path
            for comp, name, fvar in fixup_fvar:
                comp.set(name+'.filename', fvar.filename, force=True)

    def get_file_vars(self):
        """Return list of (filevarname,filevarvalue,filetrait) owned by this
        component."""

        def _recurse_get_file_vars(container, file_vars, visited, scope):
            for name, obj in container.items(type=not_event):
                if id(obj) in visited:
                    continue
                visited.add(id(obj))
                if isinstance(obj, FileValue):
                    ftrait = container.trait(name)
                    if self is scope:
                        file_vars.append((name, obj, ftrait))
                    else:
                        relpath = container.get_pathname(rel_to_scope=scope)
                        file_vars.append(('.'.join([relpath, name]),
                                            obj, ftrait))
                elif isinstance(obj, Container) and \
                     not isinstance(obj, Component):
                    _recurse_get_file_vars(obj, file_vars, visited, scope)

        file_vars = []
        _recurse_get_file_vars(self, file_vars, set(), self)
        return file_vars

    def _relpath(self, path1, path2):
        """Return path for path1 relative to path2."""
        rpath = _relpath(path1, path2)
        if rpath is None:            
            self.raise_exception("'%s' has no common prefix with '%s'"
                                 % (path1, path2), ValueError)
        return rpath

    def check_save_load(self, py_dir=None, test_dir='test_dir', cleanup=True,
                        format=SAVE_CPICKLE, logfile=None, python=None):
        """Convenience routine to check that saving & reloading work.
        It will create an egg in the current directory, unpack it in `test_dir`
        via a separate process, and then load and run the component in
        another subprocess.  Returns first non-zero subprocess exit code,
        or zero if everything succeeded.
        """
        if sys.platform == 'win32':
            print '\ncheck_save_load() unsupported on win32 at this time.'
            return 0  # Enable once openmdao.util.testutil.find_python works.
        old_level = self.log_level
        self.log_level = LOG_DEBUG
        start = time.time()
        egg_info = self.save_to_egg(py_dir=py_dir, format=format)
        egg_name = egg_info[0]
        elapsed = time.time() - start
        size = os.path.getsize(egg_name)
        print '\nSaved %d bytes in %.2f seconds (%.2f bytes/sec)' % \
              (size, elapsed, size/elapsed)

        orig_dir = os.getcwd()
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        os.mkdir(test_dir)
        os.chdir(test_dir)
        egg_path = os.path.join('..', egg_name)
        unpacker = None
        try:
            print '\nUnpacking %s in subprocess...' % egg_name
            env = os.environ
            env['OPENMDAO_INSTALL'] = '0'
            if logfile:
                stdout = open(logfile, 'w')
                stderr = subprocess.STDOUT
            else:
                stdout = None
                stderr = None

            if sys.platform == 'win32' or python:
                if not python:
                    python = 'python'
                print '    python:', python
                unpacker = 'unpack.py'
                out = open(unpacker, 'w')
                out.write("""\
from openmdao.main.api import Component
Component.load_from_eggfile('%s', install=False)
""" % egg_path)
                out.close()
                args = [python, unpacker]
            else:
                args = ['sh', egg_path]

            retcode = subprocess.call(args, env=env,
                                      stdout=stdout, stderr=stderr)
            print '    retcode', retcode
            if retcode == 0:
                print '\nRunning in subprocess...'
                if not self.name:
                    self.name = self.get_default_name(self.parent)
                os.chdir(self.name)
                if not python:
                    python = 'python'
                retcode = subprocess.call([python, self.name+'_loader.py'],
                                          stdout=stdout, stderr=stderr)
                print '    retcode', retcode
            if logfile:
                stdout.close()
        finally:
            if unpacker and os.path.exists(unpacker):
                os.remove(unpacker)
            os.chdir(orig_dir)
            self.log_level = old_level
            if cleanup:
                os.remove(egg_name)
                shutil.rmtree(test_dir)

        return retcode

    @staticmethod
    def load(instream, format=SAVE_CPICKLE, package=None, do_post_load=True,
             top_obj=True, name=''):
        """Load object(s) from `instream`.  If `instream` is an installed
        package name, then any external files referenced in the object(s)
        are copied from the package installation to appropriate directories.
        If an external file has metadata attribute 'constant' == True and
        the machine supports it, a symlink is used rather than a file copy.
        The `package` and `top_obj` arguments are normally used by a loader
        script (generated by save_to_egg()) to load a sub-component from
        the egg.  `name` is set when creating an instance via a factory.
        In this case, external files are copied to a `name` directory and the
        component's directory attribute set accordingly.  Existing files
        are not overwritten.
        """
        top = Container.load(instream, format, package, False, name=name)
        if isinstance(top, Component):
            # Get path relative to real top before we clobber directory attr.
            if top_obj:
                relpath = '.'
            else:
                if top.parent is not None:
                    relpath = top.directory
                    obj = top.parent
                    while obj.parent is not None and \
                          isinstance(obj.parent, Component):
                        relpath = os.path.join(obj.directory, relpath)
                        obj = obj.parent
                elif top.trait('_rel_dir_path'):
                    top.warning('No parent, using saved relative directory')
                    relpath = top._rel_dir_path  # Set during save_to_egg().
                else:
                    top.warning('No parent, using null relative directory')
                    relpath = ''


            # Set top directory.
            orig_dir = os.getcwd()
            
            if name:
                top.name = name
                # New instance via create(name) gets new directory.
                if not os.path.exists(name):
                    os.mkdir(name)
                os.chdir(name)
            # TODO: (maybe) Seems like we should make top.directory relative here 
            # instead of absolute, but it doesn't work...
            #top.directory = _relpath(os.getcwd(), SimulationRoot.get_root())
            top.directory = os.getcwd()
            
            try:
                # Create any missing subdirectories.
                for component in [c for c in top.values(recurse=True)
                                          if isinstance(c,Component)]:
                    directory = component.get_abs_directory()
                    if not os.path.exists(directory):
                        os.makedirs(directory)

                # If necessary, copy files from installed egg.
                if isinstance(instream, basestring) and \
                   not os.path.exists(instream) and not os.path.isabs(instream):
                    # If we got this far, then the stuff below "can't" fail.
                    if not package:
                        dot = instream.rfind('.')
                        package = instream[:dot]
                    top._restore_files(package, relpath)
            finally:
                os.chdir(orig_dir)
                if name and not glob.glob(os.path.join(name, '*')):
                    # Cleanup unused directory.
                    os.rmdir(name)
                    top.directory = ''

        if do_post_load:
            top.post_load()
        return top

    def _restore_files(self, package, relpath):
        """Restore external files from installed egg."""
        if self.directory:
            self.push_dir(self.get_abs_directory())
        try:
            fvars = self.get_file_vars()
            if self.external_files or fvars:
                self.info('Restoring files in %s', os.getcwd())

            for metadata in self.external_files:
                pattern = metadata['path']
                if not pattern:
                    continue
                is_input = metadata.get('input', False)
                const = metadata.get('constant', False)
                self._copy_files(pattern, package, relpath, is_input, const)

            for fvarname, fvar, ftrait in fvars:
                pattern = fvar.filename
                if not pattern:
                    continue
                is_input = ftrait.iostatus == 'in'
                const = False
                self._copy_files(pattern, package, relpath, is_input, const)

            for component in [c for c in self.values(recurse=False)
                                    if isinstance(c, Component)]:
                path = relpath
                if component.directory:
                    # Must use '/' for resources.
                    path += '/'+component.directory
                component._restore_files(package, path)
        finally:
            if self.directory:
                self.pop_dir()

    def _copy_files(self, pattern, package, relpath, is_input, const):
        """Copy files from installed egg matching pattern."""
        symlink = const and sys.platform != 'win32'

        directory = os.path.dirname(pattern)
        pattern = os.path.basename(pattern)
        if directory:
            if not os.path.exists(directory):
                os.makedirs(directory)
            # Must use '/' for resources.
            relpath = relpath+'/'+directory

        relpath = os.path.normpath(relpath)
        pkg_files = pkg_resources.resource_listdir(package, relpath)

        if directory:
            self.push_dir(directory)
        try:
            found = False
            for filename in pkg_files:
                if fnmatch.fnmatch(filename, pattern):
                    found = True
                    if os.path.exists(filename):
                        # Don't overwrite existing files (reloaded instance).
                        self.debug("    '%s' exists", filename)
                        continue
                    # Must use '/' for resources.
                    src_name = relpath+'/'+filename
                    self.debug("    '%s'", src_name)
                    if symlink:
                        src = pkg_resources.resource_filename(package, src_name)
                        dst = filename
                        os.symlink(src, dst)
                    else:
                        src = pkg_resources.resource_stream(package, src_name)
                        dst = open(filename, 'w')
                        dst.write(src.read())
                        dst.close()
            if not found and is_input:
                self.warning("No files found for '%s'", pattern)
        finally:
            if directory:
                self.pop_dir()

    def step (self):
        """For Components that run other components (e.g., Assembly or Drivers),
        this will run one Component and return. For simple components, it is
        the same as run().
        """
        self.run()

    def stop (self):
        """Stop this component."""
        self._stop = True

    def invalidate_deps(self, vars, notify_parent=False):
        """Invalidate all of our valid outputs."""
        valid_outs = self.list_outputs(valid=True)
        
        for var in vars:
            self.set_valid(var, False)
            
        if notify_parent and self.parent and len(valid_outs) > 0:
            self.parent.invalidate_deps(['.'.join([self.name,n]) for n in valid_outs], 
                                        notify_parent)
        for out in valid_outs:
            self._valid_dict[out] = False
            
        return valid_outs    

    def update_outputs(self, outnames):
        """Do what is necessary to make the specified output Variables valid.
        For a simple Component, this will result in a run().
        """
        self.run()
        
# TODO: uncomment require_gradients and require_hessians after they're better thought out
    
    #def require_gradients (self, varname, gradients):
        #"""Requests that the component be able to provide (after execution) a
        #list of gradients w.r.t. a list of variables. The format
        #of the gradients list is [dvar_1, dvar_2, ..., dvar_n]. The component
        #should return a list with entries of either a name, a tuple of the
        #form (name,index) or None.  None indicates that the component cannot
        #compute the specified derivative. name indicates the name of a
        #scalar variable in the component that contains the gradient value, and
        #(name,index) indicates the name of an array variable and the index of
        #the entry containing the gradient value. If the component cannot
        #compute any gradients of the requested varname, it can just return
        #None.
        #"""
        #return None

    #def require_hessians (self, varname, deriv_vars):
        #""" Requests that the component be able to provide (after execution)
        #the hessian w.r.t. a list of variables. The format of
        #deriv_vars is [dvar_1, dvar_2, ..., dvar_n]. The component should
        #return one of the following:

            #1) a name, which would indicate that the component contains
               #a 2D array variable or matrix containing the hessian

            #2) an array of the form 

               #[[dx1dx1, dx1dx2, ... dx1dxn],
               #[           ...             ],
               #[dxndx1, dxndx2, ... dxndxn]]

               #with entries of either name, (name,index), or None. name
               #indicates that a scalar variable in the component contains the
               #desired hessian matrix entry. (name,index) indicates that
               #an array variable contains the value at the specified index.
               #If index is a list with two entries, that indicates that
               #the variable containing the entry is a 2d array or matrix.

            #3) None, which means the the component cannot compute any values
               #of the hessian.

             #"""
        #return None
    
    
def eggsecutable():
    """Unpack egg. Not in loader to avoid 2GB problems with zipimport."""
    install = os.environ.get('OPENMDAO_INSTALL', '1')
    if install:
        install = int(install)
    debug = os.environ.get('OPENMDAO_INSTALL_DEBUG', '1')
    if debug:
        debug = int(debug)
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Skip any accidental cruft (egg *should* be at [0]).
    for path in sys.path:
        if path.endswith('.egg'):
            try:
                Component.load_from_eggfile(path, install=install)
                return
            except Exception, exc:
                print str(exc)
                sys.exit(1)
    else:
        print "Can't find an egg file on sys.path!"
        sys.exit(1)

