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
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os

from Deadline.Scripting import RepositoryUtils, ClientUtils

# def log(text):
# 	logPath = "P:\\00_Pipeline\\Scripts\\dlDependencyLog.txt"
# 	open(logPath, "a").close()
# 	with open(logPath, "a") as logFile:
# 		logFile.write( "%s %s\n" % (ClientUtils.GetDeadlineMajorVersion(), text))


# perform: "Tools->Perform pending job scan" in super user mode to the log in Deadline console


def splitext(path):
    if path.endswith(".bgeo.sc"):
        return [path[: -len(".bgeo.sc")], ".bgeo.sc"]
    else:
        return os.path.splitext(path)


def __main__(jobId, taskIds=None):
    job = RepositoryUtils.GetJob(jobId, True)
    jobTasks = RepositoryUtils.GetJobTasks(job, True)

    import os

    depfile = os.path.join(RepositoryUtils.GetJobAuxiliaryPath(job), "dependencies.txt")
    ClientUtils.LogText("\nPrism - starting dependency scan for job %s" % jobId)
    ClientUtils.LogText("\nPrism - Dependency filepath: %s" % depfile)

    if not taskIds:

        if os.path.exists(depfile):
            with open(depfile, "r") as dependFile:
                depData = dependFile.readlines()
                depData = [x.replace("\n", "") for x in depData]

            curFrames = job.JobFramesList

            for i in range(int(len(depData) / 2)):
                offset = depData[i * 2]
                depPath, depExt = splitext(depData[1 + (i * 2)])
                for k in curFrames:
                    if not os.path.exists(
                        depPath[:-4] + format(k + int(offset), "04") + depExt
                    ):
                        ClientUtils.LogText("\nPrism - " + str(jobId) + " not released")
                        return False

            ClientUtils.LogText("\nPrism - " + str(jobId) + " released")
            return True
        else:
            ClientUtils.LogText("\nPrism - " + str(jobId) + "- No Dependency File")

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
                for i in range(int(len(depData) / 2)):
                    offset = depData[i * 2]
                    depPath, depExt = splitext(depData[1 + (i * 2)])
                    for k in curFrames:
                        filepath = depPath[:-4] + format(k + int(offset), "04") + depExt
                        exists = os.path.exists(filepath)
                        ClientUtils.LogText("checking if file exists: %s - %s" % (filepath, exists))
                        if not exists:
                            release = False
                            break
                    else:
                        continue
                    break

                if release:
                    tasksToRelease.append(taskID)

            msg = "\nPrism - Checked task ids: %s - released tasks: %s" % (taskIds, tasksToRelease)
            ClientUtils.LogText(msg)
            # log("\n" + str(jobId) + "\n" + str(taskIds) + "-" + str(tasksToRelease))
        else:
            ClientUtils.LogText("\nPrism - " + str(jobId) + "- No Dependency File")
            # log("\n" + str(jobId) + "- No Dependency File")

        return tasksToRelease
