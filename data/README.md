# BLACKICE Data Directory

This directory contains data files for the BLACKICE regime detection system.

## Files

- `machine_meta.csv` - Machine metadata (type, cluster, capacity)

## Data Sources

The main `machine_usage.csv` file is expected to be in the parent directory
due to its large size. It's read in streaming chunks to maintain constant
memory usage.

## Schema

### machine_usage.csv
| Column | Type | Description |
|--------|------|-------------|
| machine_id | string | Machine identifier |
| timestamp | int | Monotonic timestamp |
| cpu_util | int | CPU utilization (0-100) |
| mem_util | int | Memory utilization (0-100) |

### machine_meta.csv
| Column | Type | Description |
|--------|------|-------------|
| machine_id | string | Machine identifier |
| timestamp | int | Status timestamp |
| type_code | int | Machine type |
| cluster_code | int | Cluster/rack identifier |
| capacity_1 | int | CPU capacity |
| capacity_2 | int | Memory capacity |
| status | string | Current status |
