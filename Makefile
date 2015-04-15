SHELL := bash -e
SRCDIR := $(shell echo $$(pwd))/src
WORKDIR := /tmp/vmconstruct-build
INSTALLDIR := /tmp/vmconstruct-install
PKGNAME := vmconstruct

all :
	rm -rf $(INSTALLDIR)
	mkdir -p $(WORKDIR) $(INSTALLDIR)
	rsync --delete -ca $(SRCDIR)/ $(WORKDIR)

	cd $(WORKDIR) && \
	python3 setup.py bdist_egg

	#PYTHONPATH=$(SRCDIR) $(SRCDIR)/test.py

	# Create documentation ; \
	mkdir -p $(INSTALLDIR)/usr/local/share/doc/$(PKGNAME) ; \
	sphinx-apidoc -f -o doc/source $(WORKDIR)/vmconstruct ; \
	$(MAKE) -C doc PYTHONPATH=$(WORKDIR) SPHINXOPTS="-n" BUILDDIR="$(INSTALLDIR)/usr/local/share/doc/$(PKGNAME)" html

	# Install .egg to $(INSTALLDIR) ; \
	mkdir -p $(INSTALLDIR)/usr/local/share/egg/ ; \
		 VERSION=$$(<$(WORKDIR)/.__version__) ; \
		install -D -o root -g root $(WORKDIR)/dist/vmconstruct-$${VERSION}-py3.4.egg $(INSTALLDIR)/usr/local/share/egg/ && \
		(cd $(INSTALLDIR)/usr/local/share/egg/ && ln -s vmconstruct-$${VERSION}-py3.4.egg vmconstruct-LATEST-py3.4.egg)

	easy_install-3.4 -Z $(INSTALLDIR)/usr/local/share/egg/vmconstruct-$$(<$(WORKDIR)/.__version__)-py3.4.egg
