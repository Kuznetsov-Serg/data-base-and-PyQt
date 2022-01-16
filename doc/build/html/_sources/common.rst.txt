Common package
=================================================

A package of common utilities used in different modules of the project.

Script decos.py
---------------

.. automodule:: common.decos
	:members:
	
Script descryptors.py
---------------------

.. autoclass:: common.descryptors.Port
    :members:
   
Script errors.py
---------------------
   
.. autoclass:: common.errors.ServerError
   :members:
   
Script metaclasses.py
-----------------------

.. autoclass:: common.metaclasses.ServerMaker
   :members:
   
.. autoclass:: common.metaclasses.ClientMaker
   :members:
   
Script utils.py
---------------------

common.utils. **get_message** (client)


	The function of receiving messages from remote computers. Accepts JSON messages,
	decodes the received message and verifies that a dictionary has been received.

common.utils. **send_message** (sock, message)


	The function of sending dictionaries via socket. Encodes the dictionary in JSON format and sends it via socket.


Script variables.py
---------------------

Contains various global project variables.
