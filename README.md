# winpdb

This is a pretty ugly hack to get this very useful program working with Python 3 and wxPython Phoenix 4.0. 

The program works for the most part, but the namespace viewer is not working completely. This is due to significant changes in the wx.TreeListCtrl class. The file "Original_Namespace_class.py" has the original version. It is possible that "todo" updates for Phoenix will allow the original version to be used with very modest change, but more than likely the namespace method will need substantial revision.

The layout for this version is not as clean as the original, but can be adjusted to work. 

On the whole, it's still very effective for debugging.

