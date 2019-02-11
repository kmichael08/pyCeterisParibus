import json
import logging
import os
import webbrowser

from flask import Flask, render_template

from ceteris_paribus.plots import PLOTS_DIR

app = Flask(__name__, template_folder=PLOTS_DIR)

MAX_PLOTS_PER_SESSION = 10000
# generates ids for subsequent plots
number = iter(range(MAX_PLOTS_PER_SESSION))


def _calculate_plot_variables(cp_profile, selected_variables):
    """
    Helper function to calculate valid subset of variables to be plotted
    """
    if not selected_variables:
        return cp_profile.selected_variables
    if not set(selected_variables).issubset(set(cp_profile.selected_variables)):
        logging.warning("Selected variables are not subset of all variables. Parameter is ignored.")
        return cp_profile.selected_variables
    else:
        return list(selected_variables)


def _params_update(params, **kwargs):
    for key, val in kwargs.items():
        if val:
            params[key] = val
    return params


def _detect_plot_destination(destination):
    """
    Detect plot destination (browser or embedded inside a notebook) based on the user choice
    """
    if destination is None or destination == "notebook":
        try:
            from IPython.display import IFrame
            return "notebook"
        except ImportError:
            if destination == "notebook":
                logging.warning("Notebook environment not detected. Plots will be placed in a new tab")
    # when browser is explicitly chosen or as a default
    return "browser"


def plot(cp_profile, *args, destination=None,
         show_profiles=True, show_observations=True, show_residuals=False, show_rugs=False,
         aggregate_profiles=None, selected_variables=None,
         color=None, size=2, alpha=0.4,
         color_pdps=None, size_pdps=None, alpha_pdps=None,
         color_points=None, size_points=None, alpha_points=None,
         color_residuals=None, size_residuals=None, alpha_residuals=None,
         height=500, width=600,
         plot_title='', y_label='y',
         print_observations=True,
         **kwargs):
    """
    Plot ceteris paribus profile

    :param cp_profile: ceteris paribus profile
    :param args: next (optional) ceteris paribus profiles to be plotted along
    :param destination: available *browser* - open plot in a new tab, *notebook* - embed a plot in jupyter notebook, None - autodetect the best option
    :param show_profiles: whether to show profiles
    :param show_observations: whether to show individual observations
    :param show_residuals: whether to plot residuals
    :param show_rugs: whether to plot rugs
    :param aggregate_profiles: if specified additional aggregated profile will be plotted, available values: `mean`, `median`
    :param selected_variables: variables selected for the plots
    :param color: color for profiles - either a color or a variable that should be used for coloring
    :param size: size of lines to be plotted
    :param alpha: opacity of lines (between 0 and 1)
    :param color_pdps: color of pdps - aggregated profiles
    :param size_pdps: size of pdps - aggregated profiles
    :param alpha_pdps: opacity of pdps - aggregated profiles
    :param color_points: color points to be plotted
    :param size_points: size of points to be plotted
    :param alpha_points: opacity of points
    :param color_residuals: color of plotted residuals
    :param size_residuals: size of plotted residuals
    :param alpha_residuals: opacity of plotted residuals
    :param height: height of the window containing plots
    :param width: width of the window containing plots
    :param plot_title: Title of the plot displayed above
    :param y_label: Label for the y axis
    :param print_observations: whether to print the table with observations values
    :param kwargs: other options passed to the plot
    """

    params = dict()
    params.update(kwargs)
    params["variables"] = _calculate_plot_variables(cp_profile, selected_variables)
    params['color'] = "_label_" if args else color
    params['show_profiles'] = show_profiles
    params['show_observations'] = show_observations
    params['show_rugs'] = show_rugs
    params['show_residuals'] = show_residuals and (cp_profile.new_observation_true is not None)
    params['add_table'] = print_observations
    params['height'] = height
    params['width'] = width
    params['plot_title'] = plot_title
    params['size_ices'] = size
    params['alpha_ices'] = alpha
    params = _params_update(params,
                            color_pdps=color_pdps, size_pdps=size_pdps, alpha_pdps=alpha_pdps,
                            size_points=size_points, alpha_points=alpha_points, color_points=color_points,
                            size_residuals=size_residuals, alpha_residuals=alpha_residuals,
                            color_residuals=color_residuals,
                            y_label=y_label)

    if aggregate_profiles in {'mean', 'median', None}:
        params['aggregate_profiles'] = aggregate_profiles
    else:
        logging.warning("Incorrect function for profile aggregation: {}. Parameter ignored."
                        "Available values are: 'mean' and 'median'".format(aggregate_profiles))
        params['aggregate_profiles'] = None

    plot_id = str(next(number))
    with open(os.path.join(PLOTS_DIR, "params{}.js".format(plot_id)), 'w') as f:
        f.write("params = " + json.dumps(params, indent=2) + ";")

    all_profiles = [cp_profile] + list(args)

    cp_profile.save_observations(all_profiles, 'obs{}.js'.format(plot_id))
    cp_profile.save_profiles(all_profiles, "profile{}.js".format(plot_id))

    with app.app_context():
        data = render_template("plot_template.html", i=plot_id, params=params)

    with open(os.path.join(PLOTS_DIR, "plots{}.html").format(plot_id), 'w') as f:
        f.write(data)

    plot_path = os.path.join(PLOTS_DIR, "plots{}.html".format(plot_id))

    destination = _detect_plot_destination(destination)
    if destination == "notebook":
        from IPython.display import IFrame, display
        display(IFrame(os.path.relpath(plot_path), width=int(width * 1.1), height=int(height * 1.1)))
    else:
        # open plot in a browser
        webbrowser.open("file://{}".format(plot_path))
