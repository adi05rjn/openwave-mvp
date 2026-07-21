# Architecture

The MVP separates physical constants, structured-grid representation, sparse operators, modal physics, plotting, and CLI orchestration. The next major architectural boundary is a generic discrete-complex layer supporting nodes, edges, faces, cells, incidence matrices, and material-weighted Hodge operators. That layer will enable Nédélec FEM without coupling the solver to one mesh generator.
