# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2020 Richard Frangenberg
#
# Licensed under GNU GPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


from Deadline.Scripting import *

# def log(text):
# 	logPath = "P:\\00_Pipeline\\Scripts\\dlDependencyLog.txt"
# 	open(logPath, "a").close()
# 	with open(logPath, "a") as logFile:
# 		logFile.write( "%s %s\n" % (ClientUtils.GetDeadlineMajorVersion(), text))


# perform: "Tools->Perform pending job scan" in super user mode to the log in Deadline console


def __main__(jobId, taskIds=None):
    job = RepositoryUtils.GetJob(jobId, True)
    jobTasks = RepositoryUtils.GetJobTasks(job, True)

    import os

    depfile = os.path.join(RepositoryUtils.GetJobAuxiliaryPath(job), "dependencies.txt")
    ClientUtils.LogText("\nPrism - starting dependency scan for job %s" % jobId)
    ClientUtils.LogText("\nDependency filepath: %s" % depfile)

    if not taskIds:

        if os.path.exists(depfile):
            with open(depfile, "r") as dependFile:
                depData = dependFile.readlines()
                depData = [x.replace("\n", "") for x in depData]

            curFrames = job.JobFramesList
            releaseJob = True

            for i in range(len(depData) / 2):
                offset = depData[i * 2]
                depPath = os.path.splitext(depData[1 + (i * 2)])[0]
                depExt = os.path.splitext(depData[1 + (i * 2)])[1]
                for k in curFrames:
                    if not os.path.exists(
                        depPath[:-4] + format(k + int(offset), "04") + depExt
                    ):
                        ClientUtils.LogText("\n" + str(jobId) + " not released")
                        return False

            ClientUtils.LogText("\n" + str(jobId) + " released")
            return True
        else:
            ClientUtils.LogText("\n" + str(jobId) + "- No Dependency File")

        return False
    else:

        tasksToRelease = []

        if os.path.exists(depfile):
            with open(depfile, "r") as dependFile:
                depData = dependFile.readlines()
                depData = [x.replace("\n", "") for x in depData]

            for taskID in taskIds:
                task = jobTasks.Tasks[int(taskID)]

                curFrames = task.TaskFrameList

                release = True
                for i in range(len(depData) / 2):
                    offset = depData[i * 2]
                    depPath = os.path.splitext(depData[1 + (i * 2)])[0]
                    depExt = os.path.splitext(depData[1 + (i * 2)])[1]
                    for k in curFrames:
                        ClientUtils.LogText(
                            depPath[:-4] + format(k + int(offset), "04") + depExt
                        )
                        if not os.path.exists(
                            depPath[:-4] + format(k + int(offset), "04") + depExt
                        ):
                            release = False
                            break
                    else:
                        continue
                    break

                if release:
                    tasksToRelease.append(taskID)

            ClientUtils.LogText("\n" + str(taskIds) + "-" + str(tasksToRelease))
            # log("\n" + str(jobId) + "\n" + str(taskIds) + "-" + str(tasksToRelease))
        else:
            ClientUtils.LogText("\n" + str(jobId) + "- No Dependency File")
            # log("\n" + str(jobId) + "- No Dependency File")

        return tasksToRelease
