#!/bin/bash
# DBT Manager Script

echo "Managing DBT..."

# Run DBT commands
dbt run
dbt test

echo "DBT management completed!"
