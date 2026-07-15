#!/bin/bash
# Throwaway 5-minute job to measure real H200 queue waits (kill test #2).
# Submit a few times a day for a week; then:
#   sacct -u $USER --name=queue-probe --format=JobID,Submit,Start,Elapsed
#SBATCH -J queue-probe
#SBATCH -p mit_normal_gpu
#SBATCH -G h200:2
#SBATCH -c 4
#SBATCH -t 00:05:00
#SBATCH -o /dev/null

nvidia-smi --query-gpu=name,memory.total --format=csv
sleep 60
