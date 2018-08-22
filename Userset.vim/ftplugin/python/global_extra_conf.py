
import os

DIR_OF_THIS_SCRIPT = os.path.abspath( os.path.dirname( __file__ ) )

def Settings( **kwargs ):
    return {
        'sys_path': [
            DIR_OF_THIS_SCRIPT + '/CompletePack'
        ]
    }
