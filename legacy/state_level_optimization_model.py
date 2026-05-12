import numpy as np
import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, LpMinimize, LpStatus
import os
import matplotlib.pyplot as plt


def optimize_energy_system(COST_wind, COST_battery, EFF, D, num_time_periods, CF_t, monthly_aggregation=False, yearly_aggregation=False):

    print(CF_t)

    problem = LpProblem(str(np.random.uniform(0,1)), LpMinimize)

    # Create decision variables
    w = LpVariable("w", lowBound=0.01)
    b = LpVariable("b", lowBound=0)
    w_t = [LpVariable(f"w_{t}", lowBound=0) for t in range(num_time_periods)]
    c_t = [LpVariable(f"c_{t}", lowBound=0) for t in range(num_time_periods)]
    d_t = [LpVariable(f"d_{t}", lowBound=0) for t in range(num_time_periods)]
    b_t = [LpVariable(f"b_{t}", lowBound=0) for t in range(num_time_periods)]

    # Objective function
    objective = COST_wind * w + COST_battery * b
    problem += objective

    # Adding constraints as per the given code

    # Power balance constraints
    for t in range(num_time_periods):
        problem += w_t[t] - c_t[t] + d_t[t] == D

    # Wind generation constraints
    for t in range(num_time_periods):
        problem += w_t[t] <= CF_t[t] * w

    # Battery charge constraints
    for t in range(num_time_periods):
        problem += c_t[t] <= b

    # Battery discharge constraints
    for t in range(num_time_periods):
        problem += d_t[t] <= b

    # Battery state of charge constraints
    for t in range(1, num_time_periods):
        problem += b_t[t] == b_t[t - 1] + EFF * c_t[t] - d_t[t]
        problem += b_t[t] <= b
        problem += b_t[0] == EFF * c_t[0] - d_t[0]  # Initial state of charge

    # Solve the optimization problem
    problem.solve()

    # Get the optimal values for w_t
    optimal_w_t = [w_t_var.value() for w_t_var in w_t]

    # Calculate wind supply curtailment
    wind_supply_curtailment = [CF_t[t] * w.value() - optimal_w_t[t] for t in range(num_time_periods)]
    d_t = [d_t[t].value() for t in range(num_time_periods)]

    if monthly_aggregation:
        wind_supply_curtailment = [sum(wind_supply_curtailment[month_start:month_start + hours]) for month_start, hours
                                   in zip(range(0, num_time_periods, 730),
                                          [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744])]
        d_t = [sum(d_t[month_start:month_start + hours]) for month_start, hours
                                   in zip(range(0, num_time_periods, 730),
                                          [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744])]

        CF_t = [sum(CF_t[month_start:month_start + hours]) for month_start, hours
                                   in zip(range(0, num_time_periods, 730),
                                          [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744])]

    elif yearly_aggregation:
        total_yearly_curtailment = sum(wind_supply_curtailment)
        average_monthly_curtailment = total_yearly_curtailment / 12
        wind_supply_curtailment = [average_monthly_curtailment for _ in range(12)]

        total_yearly_discharge = sum(d_t)
        average_monthly_discharge = total_yearly_discharge / 12
        d_t = [ average_monthly_discharge for _ in range(12)]

        total_yearly_capacity = sum(CF_t)
        average_monthly_discharge = total_yearly_capacity / 12
        CF_t = [average_monthly_discharge for _ in range(12)]



    return w.value(), b.value(), wind_supply_curtailment, d_t, [w.value()*i for i in CF_t]

