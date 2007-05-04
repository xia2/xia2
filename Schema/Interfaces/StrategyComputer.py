#!/usr/bin/env python
# StrategyComputer
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 4th May 2007
#
# An interface to strategy calculation - this should compute a strategy
# completely given e.g. some images and an Indexer. The Indexer is to allow
# some external control over the indexing, as this should be external. If
# the strategy computer wants to do some integration of the images (e.g.
# for BEST) then that's fine.
#
# See bug # 2335

