# ipyconsole #

An IPython console in GTK.

## Dependencies ##

* pygtk
* Bundled with IPython 0.8.4.

The API for later versions of IPython changed. Its probably possible to port but the IPython API changes a lot and it would also mean more dependencies.

## Running ##

From the terminal:

    python ipyconsole.py

As an imported module added to a container `container`:

    import ipyconsole
    scrolled_window, ipyview = ipyconsole.scrolled_ipyconsole(500, 300, user_global_ns = {"varname_inside":varname})
    container.pack_start(scrolled_window)
	scrolled_window.show_all()

Same as above without the scrolled window wrapper:

	import ipyconsole
    ipyview = ipyconsole.IPythonView()
    container.pack_start(ipyview)
	ipyview.show()

## Missing ##

Some keys related features for IPython are not there yet. Like pressing up/down for completing a line.

History and table completion do work though.
