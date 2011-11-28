SOURCE_OBJECTS = mpsa.o mpsa_Commands.o mpsa_DefnOps.o mpsa_FileCommands.o mpsa_FileOps.o mpsa_Init.o mpsa_Interface.o mpsa_ListCommand.o mpsa_ListCommands.o mpsa_ListOps.o mpsa_MovementCommands.o mpsa_MovementOps.o mpsa_Operator.o mpsa_Ops.o mpsa_ParticleCommand.o mpsa_ParticleCommands.o mpsa_ParticleExtract.o mpsa_ParticleOps.o mpsa_SimCommand.o mpsa_SimulationOps.o mpsa_TclMain.o mpsa_TclUtils.o tree_Commands.o tree_HashOps.o tree_Init.o tree_TreeOps.o cloud_Command.o cloud_Init.o cloud_Ops.o sn_Command.o sn_Init.o sn_Ops.o sf_Init.o sf_Ops.o sf_SFCommand.o mpsa_Random.o

.suffixes : .o .c
.c.o : 
	cc -c -malign-double -O3 -I/usr/include -DMPSA_ETC_DIR=\"/home/gw219/mpsa/i386/etc\" $<
mpsa : $(SOURCE_OBJECTS)
	cc -malign-double -O3 -o mpsa $(SOURCE_OBJECTS) -L/usr/lib -ltcl8.5 -lm -lc
