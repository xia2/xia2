# mpsa command file test no 2
# 25th october 2000
# g.winter

# tell the world that things are happening

puts "test: benchmark started at [exec date]: heating on"

puts [sf::sf bimodal.setup -1.35 8.9e-12 8.9e-11 3.6e-10]

# set up particle types

mpsa::pcl register star 0
mpsa::pcl register halo 0
mpsa::pcl register cloud 1 cloud
mpsa::pcl register sn 1 sn
mpsa::pcl register ob 0

# and set up the `k' parameter to try and fix the cmsi
cloud::cloud setradiusfactor 0.297

# set up parameters for different modules

set dt 0.1

cloud::cloud setfragparam 2.23e-07 1.79e-05 -1.65
sf::sf sfe 0.05 0 0 1 1
sn::sn setup 2.5e-08 1

# create a simulation

mpsa::sim create sim

# put particles into it

mpsa::pcl cff sim star 32768 initial/disk
mpsa::pcl cff sim star 16384 initial/bulge
mpsa::pcl cff sim halo 16384 initial/halo
mpsa::pcl cff sim cloud 32768 initial/clouds

# and create a few useful lists

mpsa::lst create sim list
mpsa::lst create sim starlist
mpsa::lst create sim newstarlist
mpsa::lst create sim halolist
mpsa::lst create sim cloudlist
mpsa::lst create sim extractlist
mpsa::lst create sim snlist
mpsa::lst create sim oblist

# and two trees, so that it is slightly clearer what is going on

tree::tree create gravtree
tree::tree create searchtree

# load particles into lists to initialise

mpsa::lst append list particle type int == star
mpsa::lst append list particle type int == halo
mpsa::lst append list particle type int == cloud
mpsa::lst append cloudlist particle type int == cloud

# initialise cloud temperatures and radii
cloud::cloud getpip cloudlist
cloud::cloud cool cloudlist $dt
cloud::cloud setradius cloudlist

# and set up `flag' values
mpsa::pcl zero flag list
mpsa::pcl zero extract list

# clear all lists
mpsa::lst clear list
mpsa::lst clear cloudlist

# the iterative loop - now that everything is set up!

set clms [open cloud_mass_spec w]
set clmt [open cloud_mean_temp w]
set mstar [open star_formation w]
set snfile [open sn_formation w]

for {set i 0} {$i < 51} {incr i} {
	if {[expr $i%25] == 0} {
		# save the simulation state
		mpsa::lst clear cloudlist
		# exec mkdir ./saves/save$i
		# mpsa::saver sim ./saves/save$i
	}
	puts "iteration $i at [exec date]"
	# load particles into initial lists
	puts "star  [mpsa::lst append starlist particle type int == star]"
	puts "halo  [mpsa::lst append halolist particle type int == halo]"
	puts "cloud [mpsa::lst append cloudlist particle type int == cloud]"

	# merge very small star clusters
	tree::tree load searchtree starlist
	tree::tree merge searchtree 0.1 2e-05
	tree::tree clear searchtree
	mpsa::lst append extractlist particle flag int == 1 from starlist
	mpsa::pcl delete extractlist
	mpsa::lst clear extractlist
	mpsa::lst clear starlist
        puts "star  [mpsa::lst append starlist particle type int == star]"
	puts "ob    [mpsa::lst append starlist particle type int == ob]"

	puts "cloud index: [mpsa::pcl mspec cloudlist]"
	puts "cloud T:     [mpsa::lst massaveraged cloudlist cloud t]"
	puts $clms "$i     [mpsa::pcl mspec cloudlist]"
	puts $clmt "$i     [mpsa::lst massaveraged cloudlist cloud t]"

	# update v by half timestep and x by one..
	mpsa::pcl dv starlist [expr $dt / 2]
	mpsa::pcl dv halolist [expr $dt / 2]
	mpsa::pcl dv cloudlist [expr $dt / 2]
	mpsa::pcl dx starlist $dt 
	mpsa::pcl dx halolist $dt
	mpsa::pcl dx cloudlist $dt

	# reset the accelerations
	mpsa::lst zero starlist
 	mpsa::lst zero halolist
	mpsa::lst zero cloudlist

	# calculation of gravitational forces - first from halo
	tree::tree setup 0.7 0.4
	tree::tree load gravtree halolist
	puts "halo [tree::tree calccom gravtree]"
	tree::tree calcgrav gravtree halolist
	tree::tree calcgrav gravtree starlist
	tree::tree calcgrav gravtree cloudlist
	tree::tree clear gravtree

	# calculation of gravitational forces - then from stars
	tree::tree setup 0.7 0.1
	tree::tree load gravtree starlist
	puts "star [tree::tree calccom gravtree]"
	tree::tree calcgrav gravtree halolist
	tree::tree calcgrav gravtree starlist
	tree::tree calcgrav gravtree cloudlist
	tree::tree clear gravtree

	# calculation of gravitational forces - then from clouds
	tree::tree setup 0.7 0.1
	tree::tree load gravtree cloudlist
	puts "cloud [tree::tree calccom gravtree]"
	tree::tree calcgrav gravtree halolist
	tree::tree calcgrav gravtree starlist
	tree::tree calcgrav gravtree cloudlist
	tree::tree clear gravtree

	# find supernovae 
	mpsa::lst append oblist particle type int == ob
	sn::sn startsn oblist sn
	puts "[mpsa::lst append snlist particle type int == sn] sne"
	puts $snfile " $i [mpsa::lst append extractlist particle age float == 0 from snlist]"
	mpsa::lst clear extractlist
	mpsa::lst clear oblist

	# calculate sn-cloud interaction
	cloud::cloud getpip cloudlist
	tree::tree load searchtree cloudlist
	sn::sn shock snlist searchtree $dt
	tree::tree clear searchtree
	mpsa::lst append extractlist particle extract int == 1 from cloudlist
	mpsa::pcl delete extractlist
	mpsa::lst clear cloudlist
	mpsa::lst clear extractlist

	# find cloud cloud collisions
	mpsa::lst append cloudlist particle type int == cloud
	cloud::cloud setradius cloudlist
	cloud::cloud setrho cloudlist
	tree::tree load searchtree cloudlist
	cloud::cloud findcollisions cloudlist searchtree
	tree::tree clear searchtree
	mpsa::lst append extractlist particle flag int == 1 from cloudlist
	mpsa::pcl delete extractlist
	mpsa::lst clear cloudlist
	mpsa::lst clear extractlist

	# calculate star formation
	mpsa::lst append cloudlist particle type int == cloud

	# set the radii of the clouds, to prevent two particles in one place
	cloud::cloud setradius cloudlist

	sf::sf bimodal.form cloudlist 7.5e-04 15 -3 star ob

	# this will have to be looked at - add a notempincrease option?

	mpsa::lst append newstarlist particle type int == star
	mpsa::lst append extractlist particle age float == 0 from newstarlist
	puts "mass in new stars: [mpsa::lst mass extractlist]"
	puts $mstar "$i [mpsa::lst mass extractlist]"
	mpsa::lst clear extractlist
	mpsa::lst clear newstarlist
	mpsa::lst clear cloudlist

	# fragment very warm clouds

	mpsa::lst append cloudlist particle type int == cloud	
	cloud::cloud deshock cloudlist
	mpsa::lst append extractlist cloud t float > 4900 from cloudlist
	cloud::cloud fragment extractlist
	mpsa::lst clear cloudlist
	mpsa::lst clear extractlist

	# cool all of the clouds
	puts "[mpsa::lst append cloudlist particle type int == cloud] clouds"
	cloud::cloud getpip cloudlist
	cloud::cloud cool cloudlist $dt
	puts "clouds cooled"

	# update all of the supernova remnants
	sn::sn update snlist $dt
	puts "[mpsa::lst append extractlist sn speed float < 0.05 from snlist] dead sne"
	mpsa::pcl delete extractlist
	mpsa::lst clear snlist
	mpsa::lst clear extractlist

	# star list will have changed (star formation and ob death)
	mpsa::lst clear starlist
	puts "star [mpsa::lst append starlist particle type int == star]"
	puts "ob   [mpsa::lst append starlist particle type int == ob]"

	# finish updating the velocities
	mpsa::pcl dv starlist [expr $dt / 2]
	mpsa::pcl dv halolist [expr $dt / 2]
	mpsa::pcl dv cloudlist [expr $dt / 2]

	# clear the lists
	mpsa::lst clear cloudlist
	mpsa::lst clear starlist
	mpsa::lst clear halolist
	mpsa::sim age sim $dt

	flush $clms
	flush $clmt	
	flush $mstar
}

close $clms
close $clmt
close $mstar
close $snfile
