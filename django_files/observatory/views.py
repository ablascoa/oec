# -*- coding: utf-8 -*-
# Django
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.template import RequestContext
from django.core.urlresolvers import resolve
# General
import json
# Project specific
from django.utils.translation import gettext as _
# App specific
from observatory.models import *

def home(request):
	try:
		ip = request.META["HTTP_X_FORWARDED_FOR"]
	except KeyError:
		ip = request.META["REMOTE_ADDR"]
	return render_to_response("home.html", context_instance=RequestContext(request))

def about(request):
	return render_to_response("about/index.html", context_instance=RequestContext(request))
def team(request):
	return render_to_response("about/team.html", context_instance=RequestContext(request))
def permissions(request):
	return render_to_response("about/permissions.html", context_instance=RequestContext(request))

def api(request):
	return render_to_response("api/index.html", context_instance=RequestContext(request))

def api_apps(request):
	return render_to_response("api/apps.html", context_instance=RequestContext(request))

def api_data(request):
	return render_to_response("api/data.html", context_instance=RequestContext(request))

def book(request):
	return render_to_response("book/index.html", context_instance=RequestContext(request))

def set_language(request, lang):
	next = request.REQUEST.get('next', None)
	if not next:
		next = request.META.get('HTTP_REFERER', None)
	if not next:
		next = '/'
	response = HttpResponseRedirect(next)
	# if request.method == 'GET':
	# 	lang_code = request.GET.get('language', None)
	lang_code = lang
	if lang_code:
		if hasattr(request, 'session'):
			request.session['django_language'] = lang_code
		else:
			response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
			translation.activate(lang_code)
	return response

def download(request):
	try:
		import cairo, rsvg, xml.dom.minidom
	except:
		pass
	import csv
	content = request.POST.get("content")
	title = request.POST.get("title")
	format = request.POST.get("format")
	
	if format == "svg" or format == "pdf" or format == "png":
		svg = rsvg.Handle(data=content.encode("utf-8"))
		x = width = svg.props.width
		y = height = svg.props.height
	
	if format == "svg":
		response = HttpResponse(svg_xml, mimetype="application/octet-stream")
			
	elif format == "pdf":	
		response = HttpResponse(mimetype='application/pdf')
		surf = cairo.PDFSurface(response, x, y)
		cr = cairo.Context(surf)
		svg.render_cairo(cr)
		surf.finish()
	
	elif format == "png":	
		response = HttpResponse(mimetype='image/png')
		surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, x, y)
		cr = cairo.Context(surf)
		svg.render_cairo(cr)
		surf.write_to_png(response)
	
	else:
		response = HttpResponse(mimetype="text/csv")
		csv_writer = csv.writer(response, delimiter=',', quotechar='"')#, quoting=csv.QUOTE_MINIMAL)
		csv_writer.writerows(json.loads(content))
	
	# Need to change with actual title
	response["Content-Disposition"]= "attachment; filename=%s.%s" % (title, format)
	
	return response

def app(request, app_name, trade_flow, filter, year):
	# Get URL query parameters
	format = request.GET.get("format", False)
	lang = request.GET.get("lang", False)
	crawler = request.GET.get("_escaped_fragment_", False)
	
	country1, country2, product = None, None, None
	country1_list, country2_list, product_list, year1_list, year2_list, year_interval_list, year_interval = None, None, None, None, None, None, None
	
	trade_flow_list = ["export", "import", "net_export", "net_import"]
	
	year1_list = range(1962, 2010, 1)
	if "." in year:
		y = [int(x) for x in year.split(".")]
		year = range(y[0], y[1]+1, y[2])
		year2_list = year1_list
		year_interval_list = range(1, 11)
		year_interval = year[1] - year[0]
	else:
		year = int(year)
	
	json_response = {
		"year": year,
		"app": app_name
	}
	
	# Bilateral
	if "." in filter:
		bilateral_filters = filter.split(".")
		
		# Country x Product
		if len(bilateral_filters[1]) > 3:
			country1 = Country.objects.get(name_3char=bilateral_filters[0])
			product = Sitc4.objects.get(code=bilateral_filters[1])
			
			# Lists used for control pane
			country1_list = Country.objects.get_all(lang)
			product_list = Sitc4.objects.get_all(lang)
			trade_flow_list = ["export", "import"]
			
			article = "to" if trade_flow == "export" else "from"
			title = "Where does %s %s %s %s?" % (country1.name, trade_flow, product.name_en, article)
			
			# cspy means country1 / countr2 / show / year
			if crawler == "" or format == "json":
				json_response["data"] = Sitc4_ccpy.objects.cspy(country1, product, trade_flow)
				json_response["attr_data"] = Country.objects.get_all(lang)
				json_response["title"] = title
			
		# Country x Country
		else:
			country1 = Country.objects.get(name_3char=bilateral_filters[0])
			country2 = Country.objects.get(name_3char=bilateral_filters[1])

			# Lists used for control pane
			country1_list = Country.objects.get_all(lang)
			country2_list = country1_list
			trade_flow_list = ["export", "import"]
			
			article = "to" if trade_flow == "export" else "from"
			title = "What does %s %s %s %s?" % (country1.name, trade_flow, article, country2.name)
			
			# ccsy means country1 / countr2 / show / year
			if crawler == "" or format == "json":
				json_response["data"] = Sitc4_ccpy.objects.ccsy(country1, country2, trade_flow)
				json_response["attr_data"] = Sitc4.objects.get_all(lang)
				json_response["title"] = title
	
	# Product
	elif len(filter) > 3:
		product = Sitc4.objects.get(code=filter)
		product_list = Sitc4.objects.get_all(lang)
				
		title = "Who %ss %s?" % (trade_flow.replace("_", " "), product.name_en)
		
		# sapy means show / all / product / year
		if crawler == "" or format == "json":
			json_response["data"] = Sitc4_cpy.objects.sapy(product, trade_flow)
			json_response["attr_data"] = Country.objects.get_all(lang)
			json_response["title"] = title
	
	# Country
	else:
		country1 = Country.objects.get(name_3char=filter)
		country1_list = Country.objects.get_all(lang)
		
		title = "What does %s %s?" % (country1.name, trade_flow.replace("_", " "))
		
		# casy means country1 / all / show / year
		if crawler == "" or format == "json":
			json_response["data"] = Sitc4_cpy.objects.casy(country1, trade_flow)
			json_response["attr_data"] = Sitc4.objects.get_all(lang)
			json_response["title"] = title
	
	# Send data as JSON to browser via AJAX
	if format == "json":
		return HttpResponse(json.dumps(json_response))
	
	# Return page without visualization data
	return render_to_response("app/index.html", {
		"title": title,
		"trade_flow": trade_flow,
		"country1": country1,
		"country2": country2,
		"product": product,
		"year": year,
		"trade_flow_list": trade_flow_list,
		"country1_list": country1_list,
		"country2_list": country2_list,
		"product_list": product_list,
		"year1_list": year1_list,
		"year2_list": year2_list,
		"year_interval": year_interval,
		"year_interval_list": year_interval_list}, context_instance=RequestContext(request))

def app_redirect(request, app_name, trade_flow, filter, year):
	# Corrent for old spelling of tree map as one word
	if app_name == "treemap":
		app_name = "tree_map"
	
	# Bilateral
	if "." in filter:
		bilateral_filters = filter.split(".")
		
		# Country x Product
		if len(bilateral_filters[1]) > 3:
			country1, country2, product = bilateral_filters[0], "show", bilateral_filters[1]
			
		# Country x Country
		else:
			country1, country2, product = bilateral_filters[0], bilateral_filters[1], "show"
	
	# Product
	elif len(filter) > 3:
		country1, country2, product = "show", "all", filter
	
	# Country
	else:
		country1, country2, product = filter, "all", "show"
	# raise Exception("/explore/%s/%s/%s/%s/%s/%s/" % (app_name, trade_flow, country1, country2, product, year))
	return HttpResponsePermanentRedirect("/explore/%s/%s/%s/%s/%s/%s/" % (app_name, trade_flow, country1, country2, product, year))

def explore(request, app_name, trade_flow, country1, country2, product, year):
	# raise Exception(country1, country2, product, year)
	# Get URL query parameters
	crawler = request.GET.get("_escaped_fragment_", False)
	options = request.GET.copy()
	# lang = request.GET.get("lang", False)
	if 'django_language' in request.session:
		lang = request.session['django_language']
	else:
		lang = "en"
	lang = request.GET.get("lang", lang)
	options["lang"] = lang
	options = options.urlencode()
	
	country1_list, country2_list, product_list, year1_list, year2_list, year_interval_list, year_interval = None, None, None, None, None, None, None
	data_as_text = {}
	# What is actually being shown on the page
	item_type = "products"
	
	trade_flow_list = [("export", _("Export")), ("import", _("Import")), ("net_export", _("Net Export")), ("net_import", _("Net Import"))]
	if app_name == "product_space":
		trade_flow_list = [trade_flow_list[0]]
	
	year1_list = range(1962, 2010, 1)
	if "." in year:
		y = [int(x) for x in year.split(".")]
		# year = range(y[0], y[1]+1, y[2])
		year_start = y[0]
		year_end = y[1]
		year_interval = y[2]
		year2_list = year1_list
		year_interval_list = range(1, 11)
		# year_interval = year[1] - year[0]
	else:
		year_start, year_end, year_interval = None, None, None
		year = int(year)
	
	api_uri = "/api/%s/%s/%s/%s/%s/?%s" % (trade_flow, country1, country2, product, year, options)
	
	if crawler == "":
		# x, v = resolve(api_uri)
		view, args, kwargs = resolve("/api/%s/%s/%s/%s/%s/" % (trade_flow, country1, country2, product, year))
		kwargs['request'] = request
		# raise Exception(view(*args, **kwargs))
		view_response = view(*args, **kwargs)
		data_as_text["data"] = view_response[0]
		data_as_text["total_value"] = view_response[1]
		data_as_text["columns"] = view_response[2]
		# data = [33, 44]
		# data = {44:33}
		# raise Exception(data)
	
	# Country
	if country2 == "all" and product == "show":
		country1 = Country.objects.get(name_3char=country1)
		country1_list = Country.objects.get_all(lang)
		
		# country2, product = None, None
		
		title = "What does %s %s?" % (country1.name, trade_flow.replace("_", " "))
	
	# Country but showing other country trade partners
	elif country2 == "show" and product == "all":
		country1 = Country.objects.get(name_3char=country1)
		country1_list = Country.objects.get_all(lang)
		
		item_type = "countries"
		
		article = "to" if trade_flow == "export" else "from"
		title = "Where does %s %s %s?" % (country1.name, trade_flow.replace("_", " "), article)
	
	# Product
	elif country1 == "show" and country2 == "all":
		product = Sitc4.objects.get(code=product)
		product_list = Sitc4.objects.get_all(lang)
		
		item_type = "countries"
		
		title = "Who %ss %s?" % (trade_flow.replace("_", " "), product.name_en)
	
	# Bilateral Country x Country
	elif product == "show":
		country1 = Country.objects.get(name_3char=country1)
		country2 = Country.objects.get(name_3char=country2)

		# Lists used for control pane
		country1_list = Country.objects.get_all(lang)
		country2_list = country1_list
		# trade_flow_list = ["export", "import"]
		if _("net_export") in trade_flow_list: del trade_flow_list[trade_flow_list.index(_("net_export"))]
		if _("net_import") in trade_flow_list: del trade_flow_list[trade_flow_list.index(_("net_import"))]
		
		# product = None
		
		article = "to" if trade_flow == "export" else "from"
		title = "What does %s %s %s %s?" % (country1.name, trade_flow, article, country2.name)
	
	else:
		country1 = Country.objects.get(name_3char=country1)
		product = Sitc4.objects.get(code=product)
		
		# Lists used for control pane
		country1_list = Country.objects.get_all(lang)
		product_list = Sitc4.objects.get_all(lang)
		if "net_export" in trade_flow_list: del trade_flow_list[trade_flow_list.index("net_export")]
		if "net_import" in trade_flow_list: del trade_flow_list[trade_flow_list.index("net_import")]
		
		item_type = "countries"
		
		article = "to" if trade_flow == "export" else "from"
		title = "Where does %s %s %s %s?" % (country1.name, trade_flow, product.name_en, article)
	
	# Return page without visualization data
	return render_to_response("explore/index.html", {
		"data_as_text": data_as_text,
		"app_name": app_name,
		"title": title,
		"trade_flow": trade_flow,
		"country1": country1,
		"country2": country2,
		"product": product,
		"year": year,
		"year_start": year_start,
		"year_end": year_end,
		"year_interval": year_interval,
		"trade_flow_list": trade_flow_list,
		"country1_list": country1_list,
		"country2_list": country2_list,
		"product_list": product_list,
		"year1_list": year1_list,
		"year2_list": year2_list,
		"year_interval_list": year_interval_list,
		"api_uri": api_uri,
		"item_type": item_type}, context_instance=RequestContext(request))

def api_casy(request, trade_flow, country1, year):
	crawler = request.GET.get("_escaped_fragment_", False)
	# lang = request.GET.get("lang", "en")
	
	if 'django_language' in request.session:
		lang = request.session['django_language']
	else:
		lang = "en"
	lang = request.GET.get("lang", lang)
	
	query_params = request.GET.copy()
	query_params["lang"] = lang
	
	country1 = Country.objects.get(name_3char=country1)
	
	if crawler == "":
		db_response = Sitc4_cpy.objects.casy(country1, trade_flow, year, lang)
		data = [list(x) + [(x[3] / db_response["sum"][x[0]])*100] for x in list(db_response["data"])]
		return [data, db_response["sum"], db_response["columns"]]
	
	json_response = {}
	
	# casy means country1 / all / show / year
	# raise Exception(Sitc4_cpy.objects.casy(country1, trade_flow))
	json_response["data"] = Sitc4_cpy.objects.casy(country1, trade_flow)
	json_response["attr_data"] = Sitc4.objects.get_all(lang)
	json_response["country1"] = country1.to_json()
	json_response["title"] = "What does %s %s?" % (country1.name, trade_flow.replace("_", " "))
	json_response["year"] = year
	json_response["other"] = query_params
	if "." in year:
		year_parts = [int(x) for x in year.split(".")]
		json_response["year_start"] = year_parts[0]
		json_response["year_end"] = year_parts[1]
		json_response["year_interval"] = year_parts[2]

	return HttpResponse(json.dumps(json_response))

def api_sapy(request, trade_flow, product, year):
	if 'django_language' in request.session:
		lang = request.session['django_language']
	else:
		lang = "en"
	lang = request.GET.get("lang", lang)
	
	crawler = request.GET.get("_escaped_fragment_", False)
	query_params = request.GET.copy()
	query_params["lang"] = lang
	
	product = Sitc4.objects.get(code=product)
	
	if crawler == "":
		db_response = Sitc4_cpy.objects.sapy(product, trade_flow, year, lang)
		data = [list(x) + [(x[3] / db_response["sum"][x[0]])*100] for x in list(db_response["data"])]
		return [data, db_response["sum"], db_response["columns"]]
	
	json_response = {}
	
	# casy means country1 / all / show / year
	json_response["data"] = Sitc4_cpy.objects.sapy(product, trade_flow)
	json_response["attr_data"] = Country.objects.get_all(lang)
	json_response["title"] = "Who %ss %s?" % (trade_flow.replace("_", " "), product.name_en)
	json_response["product"] = product.to_json()
	json_response["year"] = year
	json_response["other"] = query_params
	if "." in year:
		year_parts = [int(x) for x in year.split(".")]
		json_response["year_start"] = year_parts[0]
		json_response["year_end"] = year_parts[1]
		json_response["year_interval"] = year_parts[2]
	
	if crawler == "":
		return Sitc4_cpy.objects.sapy(product, trade_flow, year)
	return HttpResponse(json.dumps(json_response))

def api_csay(request, trade_flow, country1, year):
	if 'django_language' in request.session:
		lang = request.session['django_language']
	else:
		lang = "en"
	lang = request.GET.get("lang", lang)
	
	crawler = request.GET.get("_escaped_fragment_", False)
	query_params = request.GET.copy()
	query_params["lang"] = lang
	
	country1 = Country.objects.get(name_3char=country1)
	
	article = "to" if trade_flow == "export" else "from"
	
	if crawler == "":
		db_response = Sitc4_ccpy.objects.csay(country1, trade_flow, year, lang)
		data = [list(x) + [(x[3] / db_response["sum"][x[0]])*100] for x in list(db_response["data"])]
		return [data, db_response["sum"], db_response["columns"]]
		# db_response = Sitc4_ccpy.objects.csay(country1, trade_flow, year, lang)
		# total_value = db_response[0]
		# data = [list(x) + [(x[2] / total_value)*100] for x in list(db_response[1])]
		# columns = db_response[2]
		# return [data, total_value, columns]
	
	json_response = {}
	
	# csay means country1 / show / all / year
	json_response["data"] = Sitc4_ccpy.objects.csay(country1, trade_flow)
	json_response["attr_data"] = Country.objects.get_all(lang)
	json_response["title"] = "Where does %s %s %s?" % (country1.name, trade_flow, article)
	json_response["country1"] = country1.to_json()
	json_response["year"] = year
	json_response["other"] = query_params
	if "." in year:
		year_parts = [int(x) for x in year.split(".")]
		json_response["year_start"] = year_parts[0]
		json_response["year_end"] = year_parts[1]
		json_response["year_interval"] = year_parts[2]
	
	return HttpResponse(json.dumps(json_response))

def api_ccsy(request, trade_flow, country1, country2, year):
	if 'django_language' in request.session:
		lang = request.session['django_language']
	else:
		lang = "en"
	lang = request.GET.get("lang", lang)
	
	crawler = request.GET.get("_escaped_fragment_", False)
	query_params = request.GET.copy()
	query_params["lang"] = lang
	
	country1 = Country.objects.get(name_3char=country1)
	country2 = Country.objects.get(name_3char=country2)
	
	article = "to" if trade_flow == "export" else "from"
	
	if crawler == "":
		db_response = Sitc4_ccpy.objects.ccsy(country1, country2, trade_flow, year, lang)
		data = [list(x) + [(x[3] / db_response["sum"][x[0]])*100] for x in list(db_response["data"])]
		return [data, db_response["sum"], db_response["columns"]]
	
	json_response = {}
	
	# ccsy means country1 / countr2 / show / year
	json_response["data"] = Sitc4_ccpy.objects.ccsy(country1, country2, trade_flow)
	json_response["attr_data"] = Sitc4.objects.get_all(lang)
	json_response["title"] = "What does %s %s %s %s?" % (country1.name, trade_flow, article, country2.name)
	json_response["country1"] = country1.to_json()
	json_response["country2"] = country2.to_json()
	json_response["year"] = year
	json_response["other"] = query_params
	if "." in year:
		year_parts = [int(x) for x in year.split(".")]
		json_response["year_start"] = year_parts[0]
		json_response["year_end"] = year_parts[1]
		json_response["year_interval"] = year_parts[2]
		
	return HttpResponse(json.dumps(json_response))

def api_cspy(request, trade_flow, country1, product, year):
	if 'django_language' in request.session:
		lang = request.session['django_language']
	else:
		lang = "en"
	lang = request.GET.get("lang", lang)
	
	crawler = request.GET.get("_escaped_fragment_", False)
	query_params = request.GET.copy()
	query_params["lang"] = lang
	
	country1 = Country.objects.get(name_3char=country1)
	product = Sitc4.objects.get(code=product)
	
	article = "to" if trade_flow == "export" else "from"
	
	if crawler == "":
		db_response = Sitc4_ccpy.objects.cspy(country1, product, trade_flow, year, lang)
		data = [list(x) + [(x[3] / db_response["sum"][x[0]])*100] for x in list(db_response["data"])]
		return [data, db_response["sum"], db_response["columns"]]
	
	json_response = {}
		
	# cspy means country1 / countr2 / show / year
	json_response["data"] = Sitc4_ccpy.objects.cspy(country1, product, trade_flow)
	json_response["attr_data"] = Country.objects.get_all(lang)
	json_response["title"] = "Where does %s %s %s %s?" % (country1.name, trade_flow, product.name_en, article)
	json_response["country1"] = country1.to_json()
	json_response["product"] = product.to_json()
	json_response["year"] = year
	json_response["other"] = query_params
	if "." in year:
		year_parts = [int(x) for x in year.split(".")]
		json_response["year_start"] = year_parts[0]
		json_response["year_end"] = year_parts[1]
		json_response["year_interval"] = year_parts[2]

	return HttpResponse(json.dumps(json_response))


# Embed for iframe
def embed(request, app_name, trade_flow, country1, country2, product, year):
	lang = request.GET.get("lang", "en")
	query_string = request.GET
	return render_to_response("explore/embed.html", {"app":app_name, "trade_flow": trade_flow, "country1":country1, "country2":country2, "product":product, "year":year, "other":json.dumps(query_string), "lang":lang})