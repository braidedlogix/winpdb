""" 
original namespace class-

GetChildrenCount and get_children are primary problems

"""



class CNamespacePanel(wx.Panel, CJobs):
    def __init__(self, *args, **kwargs):
        self.m_session_manager = kwargs.pop('session_manager')

        wx.Panel.__init__(self, *args, **kwargs)
        CJobs.__init__(self)
        
        self.init_jobs()

        self.m_async_sm = CAsyncSessionManager(self.m_session_manager, self)

        self.m_lock = threading.RLock()
        self.m_jobs = []
        self.m_n_workers = 0
        
        self.m_filter_level = 0
        self.m_key = None

        sizerv = wx.BoxSizer(wx.VERTICAL)
        
        self.m_tree = wx.gizmos.TreeListCtrl(self, -1, style = wx.TR_HIDE_ROOT | wx.TR_DEFAULT_STYLE | wx.TR_FULL_ROW_HIGHLIGHT | wx.NO_BORDER)

        self.m_tree.AddColumn(TLC_HEADER_NAME)
        self.m_tree.AddColumn(TLC_HEADER_TYPE)
        self.m_tree.AddColumn(TLC_HEADER_REPR)
        self.m_tree.SetColumnWidth(2, 800)
        self.m_tree.SetMainColumn(0) 
        self.m_tree.SetLineSpacing(0)
        
        self.m_tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnItemExpanding)
        self.m_tree.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnItemCollapsing)
        self.m_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnItemActivated)

        try:
            self.m_tree.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self.OnItemToolTip)
        except:
            pass

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroyWindow)

        sizerv.Add(self.m_tree, flag = wx.GROW, proportion = 1)
        self.SetSizer(sizerv)
        sizerv.Fit(self)


    def OnDestroyWindow(self, event):
        self.shutdown_jobs()

        
    def _clear(self):
        self.m_tree.DeleteAllItems()


    def set_filter(self, filter_level):
        self.m_filter_level = filter_level

        
    def bind_caption(self, caption_manager):
        w = self.m_tree.GetMainWindow()
        caption_manager.bind_caption(w)

        
    def OnItemActivated(self, event):
        item = event.GetItem()
        (expr, is_valid) = self.m_tree.GetPyData(item)
        if expr in [STR_NAMESPACE_LOADING, STR_NAMESPACE_DEADLOCK, rpdb2.STR_MAX_NAMESPACE_WARNING_TITLE]:
            return

        if is_valid:
            default_value = self.m_tree.GetItemText(item, 2)[1:]
        else:
            default_value = ''

        expr_dialog = CExpressionDialog(self, default_value)
        pos = self.GetPositionTuple()
        expr_dialog.SetPosition((pos[0] + 50, pos[1] + 50))
        r = expr_dialog.ShowModal()
        if r != wx.ID_OK:
            expr_dialog.Destroy()
            return

        _expr = expr_dialog.get_expression()

        expr_dialog.Destroy()

        _suite = "%s = %s" % (expr, _expr)
        
        self.m_async_sm.with_callback(self.callback_execute).execute(_suite)


    def callback_execute(self, r, exc_info):
        (t, v, tb) = exc_info

        if t != None:
            rpdb2.print_exception(t, b, tb)
            return

        (warning, error) = r
        
        if error != '':
            dlg = wx.MessageDialog(self, error, MSG_ERROR_TITLE, wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

        if not warning in g_ignored_warnings:
            dlg = wx.MessageDialog(self, MSG_WARNING_TEMPLATE % (warning, ), MSG_WARNING_TITLE, wx.OK | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_WARNING)
            res = dlg.ShowModal()
            dlg.Destroy()

            if res == wx.ID_CANCEL:
                g_ignored_warnings[warning] = True
        
        
    def OnItemToolTip(self, event):
        item = event.GetItem()

        tt = self.m_tree.GetItemText(item, 2)[1:]
        event.SetToolTip(tt)

       
    def OnItemCollapsing(self, event):
        item = event.GetItem()

        event.Skip()


    def GetChildrenCount(self, item):
        n = self.m_tree.GetChildrenCount(item)
        if n != 1:
            return n 

        child = self.get_children(item)[0]
        (expr, is_valid) = self.m_tree.GetPyData(child)

        if expr in [STR_NAMESPACE_LOADING, STR_NAMESPACE_DEADLOCK]:
            return 0

        return 1
        
        
    def expand_item(self, item, _map, froot = False, fskip_expansion_check = False):
        if not self.m_tree.ItemHasChildren(item):
            return
        
        if not froot and not fskip_expansion_check and self.m_tree.IsExpanded(item):
            return

        if self.GetChildrenCount(item) > 0:
            return
        
        (expr, is_valid) = self.m_tree.GetPyData(item)

        l = [e for e in _map if e.get(rpdb2.DICT_KEY_EXPR, None) == expr]
        if l == []:
            return None

        _r = l[0] 
        if _r is None:
            return   

        if rpdb2.DICT_KEY_ERROR in _r:
            return
        
        if _r[rpdb2.DICT_KEY_N_SUBNODES] == 0:
            self.m_tree.SetItemHasChildren(item, False)
            return

        #
        # Create a list of the subitems.
        # The list is indexed by name or directory key.
        # In case of a list, no sorting is needed.
        #

        snl = _r[rpdb2.DICT_KEY_SUBNODES] 
       
        for r in snl:
            if g_fUnicode:
                _name = r[rpdb2.DICT_KEY_NAME]
                _type = r[rpdb2.DICT_KEY_TYPE]
                _repr = r[rpdb2.DICT_KEY_REPR]
            else:
                _name = rpdb2.as_string(r[rpdb2.DICT_KEY_NAME], wx.GetDefaultPyEncoding())
                _type = rpdb2.as_string(r[rpdb2.DICT_KEY_TYPE], wx.GetDefaultPyEncoding())
                _repr = rpdb2.as_string(r[rpdb2.DICT_KEY_REPR], wx.GetDefaultPyEncoding())

            identation = '' 
            #identation = ['', '  '][os.name == rpdb2.POSIX and r[rpdb2.DICT_KEY_N_SUBNODES] == 0]

            child = self.m_tree.AppendItem(item, identation + _name)
            self.m_tree.SetItemText(child, ' ' + _repr, 2)
            self.m_tree.SetItemText(child, ' ' + _type, 1)
            self.m_tree.SetItemPyData(child, (r[rpdb2.DICT_KEY_EXPR], r[rpdb2.DICT_KEY_IS_VALID]))
            self.m_tree.SetItemHasChildren(child, (r[rpdb2.DICT_KEY_N_SUBNODES] > 0))

        self.m_tree.Expand(item)

    
    def OnItemExpanding(self, event):
        item = event.GetItem()        

        if not self.m_tree.ItemHasChildren(item):
            event.Skip()
            return
        
        if self.GetChildrenCount(item) > 0:
            event.Skip()
            self.m_tree.Refresh();
            return
            
        self.m_tree.DeleteChildren(item)
        
        child = self.m_tree.AppendItem(item, STR_NAMESPACE_LOADING)
        self.m_tree.SetItemText(child, ' ' + STR_NAMESPACE_LOADING, 2)
        self.m_tree.SetItemText(child, ' ' + STR_NAMESPACE_LOADING, 1)
        self.m_tree.SetItemPyData(child, (STR_NAMESPACE_LOADING, False))

        (expr, is_valid) = self.m_tree.GetPyData(item)

        f = lambda r, exc_info: self.callback_ns(r, exc_info, expr)        
        self.m_async_sm.with_callback(f).get_namespace([(expr, True)], self.m_filter_level)
        
        event.Skip()


    def callback_ns(self, r, exc_info, expr):
        (t, v, tb) = exc_info

        item = self.find_item(expr)
        if item == None:
            return
      
        #
        # When expanding a tree item with arrow-keys on wxPython 2.6, the 
        # temporary "loading" child is automatically selected. After 
        # replacement with real children we need to reselect the first child.
        #
        cl = self.get_children(item)
        freselect_child = len(cl) != 0 and cl[0] == self.m_tree.GetSelection()
            
        self.m_tree.DeleteChildren(item)
    
        if t != None or r is None or len(r) == 0:
            child = self.m_tree.AppendItem(item, STR_NAMESPACE_DEADLOCK)
            self.m_tree.SetItemText(child, ' ' + STR_NAMESPACE_DEADLOCK, 2)
            self.m_tree.SetItemText(child, ' ' + STR_NAMESPACE_DEADLOCK, 1)
            self.m_tree.SetItemPyData(child, (STR_NAMESPACE_DEADLOCK, False))
            self.m_tree.Expand(item)

            if freselect_child:
                self.m_tree.SelectItem(child)

            return
            
        self.expand_item(item, r, False, True)  

        if freselect_child:
            cl = self.get_children(item)
            self.m_tree.SelectItem(cl[0])

        self.m_tree.Refresh()
        

    def find_item(self, expr):
        item = self.m_tree.GetRootItem()
        while item:
            (expr2, is_valid) = self.m_tree.GetPyData(item)
            if expr2 == expr:
                return item               
                
            item = self.m_tree.GetNext(item)

        return None    
    

    def get_children(self, item):
        (child, cookie) = self.m_tree.GetFirstChild(item)
        cl = []
        
        while child and child.IsOk():
            cl.append(child)
            (child, cookie) = self.m_tree.GetNextChild(item, cookie)

        return cl    

                             
    def get_expression_list(self):
        if self.m_tree.GetCount() == 0:
            return None

        item = self.m_tree.GetRootItem()

        s = [item]
        el = []

        while len(s) > 0:
            item = s.pop(0)
            (expr, is_valid) = self.m_tree.GetPyData(item)
            fExpand = self.m_tree.IsExpanded(item) and self.GetChildrenCount(item) > 0
            if not fExpand:
                continue

            el.append((expr, True))
            items = self.get_children(item)
            s = items + s

        return el    


    def update_namespace(self, key, el):
        old_key = self.m_key
        old_el = self.get_expression_list()

        if key == old_key:
            el = old_el

        self.m_key = key

        if el is None:
            el = [(self.get_root_expr(), True)]

        self.post(el, self.m_filter_level)

        return (old_key, old_el)


    def post(self, el, filter_level):
        self.m_jobs.insert(0, (el, filter_level))

        if self.m_n_workers == 0:
            self.job_post(self.job_update_namespace, ())

        
    def job_update_namespace(self):
        while len(self.m_jobs) > 0:
            self.m_lock.acquire()
            self.m_n_workers += 1
            self.m_lock.release()
            
            try:
                del self.m_jobs[1:]
                (el, filter_level) = self.m_jobs.pop()
                rl = self.m_session_manager.get_namespace(el, filter_level)
                wx.CallAfter(self.do_update_namespace, rl)

            except (rpdb2.ThreadDone, rpdb2.NoThreads):
                wx.CallAfter(self.m_tree.DeleteAllItems)
                
            except:
                rpdb2.print_debug_exception()

            self.m_lock.acquire()
            self.m_n_workers -= 1
            self.m_lock.release()

        
    def do_update_namespace(self, rl):    
        self.m_tree.DeleteAllItems()

        root = self.m_tree.AddRoot('root')
        self.m_tree.SetItemPyData(root, (self.get_root_expr(), False))
        self.m_tree.SetItemHasChildren(root, True)

        s = [root]

        while len(s) > 0:
            item = s.pop(0)
            self.expand_item(item, rl, item is root)
            
            items = self.get_children(item)
            s = items + s

        self.m_tree.Refresh()


    def get_root_expr(self):
        """
        Over-ride in derived classes
        """
        pass
