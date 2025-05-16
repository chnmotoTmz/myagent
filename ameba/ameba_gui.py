#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from ameba_automation.gui_app import main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s',
                       filename='ameba_automation.log')
    main() 