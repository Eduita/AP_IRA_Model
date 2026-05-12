The key output of this model is the discounted cash flow model sheet explaining the cash dynamics and, eventually, the value of the process. 

Several important metrics from the discounted cash flow are required:

1) Expected NPV
2) getter methods for specific fields in the DCF

The configuration should begin with variable declarations and what they store. The user should begin by declaring the structure of the DCF. The DCF can be represented by a schema:

```custom language YAML like

# defined simulation variables
# allowed types (int, str, boolean, float)

GLOBALS:
    horizon_int: 36
    units_str: M

DCF_FIELDS:
    # CAPEX & OPEX are required fields that need to be defined

    # I am thinking allowing definitions through linear algebra here
```