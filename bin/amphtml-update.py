"""
This script is used to generate the 'class-amp-allowed-tags-generated.php'
file that is used by the class AMP_Tag_And_Attribute_Sanitizer.

A bash script, amphtml-update.sh, is provided to automatically run this script.  To run the bash script, type:

`bash amphtml-update.sh`

from within a Linux environment such as VVV.

See the Updating Allowed Tags and Attributes section of the Contributing guide
https://github.com/ampproject/amp-wp/blob/develop/contributing.md#updating-allowed-tags-and-attributes.

Then have fun sanitizing your AMP posts!
"""

import glob
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import collections
import json
import google
import imp

def Die(msg):
	print >> sys.stderr, msg
	sys.exit(1)


def SetupOutDir(out_dir):
	"""Sets up a clean output directory.

	Args:
		out_dir: directory name of the output directory.
	"""
	logging.info('entering ...')

	if os.path.exists(out_dir):
		subprocess.check_call(['rm', '-rf', out_dir])
	os.mkdir(out_dir)
	logging.info('... done')


def GenValidatorPb2Py(validator_directory, out_dir):
	"""Calls the proto compiler to generate validator_pb2.py.

	Args:
		validator_directory: directory name of the validator.
		out_dir: directory name of the output directory.
	"""
	logging.info('entering ...')

	os.chdir( validator_directory )
	subprocess.check_call(['protoc', 'validator.proto', '--python_out=%s' % out_dir])
	os.chdir( out_dir )
	open('__init__.py', 'w').close()
	logging.info('... done')


def GenValidatorProtoascii(validator_directory, out_dir):
	"""Assembles the validator protoascii file from the main and extensions.

	Args:
		validator_directory: directory for where the validator is located, inside the amphtml repo.
		out_dir: directory name of the output directory.
	"""
	logging.info('entering ...')

	protoascii_segments = [open(os.path.join(validator_directory, 'validator-main.protoascii')).read()]
	extensions = glob.glob(os.path.join(validator_directory, '../extensions/*/validator-*.protoascii'))
	extensions.sort()
	for extension in extensions:
		protoascii_segments.append(open(extension).read())
	f = open('%s/validator.protoascii' % out_dir, 'w')
	f.write(''.join(protoascii_segments))
	f.close()

	logging.info('... done')


def GeneratePHP(out_dir):
	"""Generates PHP for WordPress AMP plugin to consume.

	Args:
		validator_directory: directory for where the validator is located, inside the amphtml repo.
		out_dir: directory name of the output directory
	"""
	logging.info('entering ...')

	allowed_tags, attr_lists, descendant_lists, reference_points, versions = ParseRules(out_dir)

	#Generate the output
	out = []
	GenerateHeaderPHP(out)
	GenerateSpecVersionPHP(out, versions)
	GenerateDescendantListsPHP(out, descendant_lists)
	GenerateAllowedTagsPHP(out, allowed_tags)
	GenerateLayoutAttributesPHP(out, attr_lists)
	GenerateGlobalAttributesPHP(out, attr_lists)
	GenerateReferencePointsPHP(out, reference_points)
	GenerateFooterPHP(out)

	# join out array into a single string and remove unneeded whitespace
	output = re.sub("\\(\\s*\\)", "()", '\n'.join(out))

	# replace 'True' with true and 'False' with false
	output = re.sub("'True'", "true", output)
	output = re.sub("'False'", "false", output)

	# Write the php file to STDOUT.
	print output

	logging.info('... done')

def GenerateHeaderPHP(out):
	logging.info('entering ...')

	# Output the file's header
	out.append('<?php')
	out.append('/**')
	out.append(' * Generated by %s - do not edit.' % os.path.basename(__file__))
	out.append(' *')
	out.append(' * This is a list of HTML tags and attributes that are allowed by the')
	out.append(' * AMP specification. Note that tag names have been converted to lowercase.')
	out.append(' *')
	out.append(' * Note: This file only contains tags that are relevant to the `body` of')
	out.append(' * an AMP page. To include additional elements modify the variable')
	out.append(' * `mandatory_parent_blacklist` in the amp_wp_build.py script.')
	out.append(' *')
	out.append(' * phpcs:ignoreFile')
	out.append(' */')
	out.append('class AMP_Allowed_Tags_Generated {')
	out.append('')
	logging.info('... done')


def GenerateSpecVersionPHP(out, versions):
	logging.info('entering ...')

	# Output the version of the spec file and matching validator version
	if versions['spec_file_revision']:
		out.append('\tprivate static $spec_file_revision = %d;' % versions['spec_file_revision'])
	if versions['min_validator_revision_required']:
		out.append('\tprivate static $minimum_validator_revision_required = %d;' % versions['min_validator_revision_required'])
	logging.info('... done')

def GenerateDescendantListsPHP(out, descendant_lists):
	logging.info('entering ...')

	out.append('')
	out.append('\tprivate static $descendant_tag_lists = %s;' % Phpize( descendant_lists, 1 ).lstrip() )
	logging.info('... done')


def GenerateAllowedTagsPHP(out, allowed_tags):
	logging.info('entering ...')

  # Output the allowed tags dictionary along with each tag's allowed attributes
	out.append('')
	out.append('\tprivate static $allowed_tags = %s;' % Phpize( allowed_tags, 1 ).lstrip() )
	logging.info('... done')


def GenerateLayoutAttributesPHP(out, attr_lists):
	logging.info('entering ...')

	# Output the attribute list allowed for layouts.
	out.append('')
	out.append('\tprivate static $layout_allowed_attrs = %s;' % Phpize( attr_lists['$AMP_LAYOUT_ATTRS'], 1 ).lstrip() )
	out.append('')
	logging.info('... done')


def GenerateGlobalAttributesPHP(out, attr_lists):
	logging.info('entering ...')

	# Output the globally allowed attribute list.
	out.append('')
	out.append('\tprivate static $globally_allowed_attrs = %s;' % Phpize( attr_lists['$GLOBAL_ATTRS'], 1 ).lstrip() )
	out.append('')
	logging.info('... done')

def GenerateReferencePointsPHP(out, reference_points):
	logging.info('entering ...')

	# Output the reference points.
	out.append('')
	out.append('\tprivate static $reference_points = %s;' % Phpize( reference_points, 1 ).lstrip() )
	out.append('')
	logging.info('... done')

def GenerateFooterPHP(out):
	logging.info('entering ...')

	# Output the footer.
	out.append('''
	/**
	 * Get allowed tags.
	 *
	 * @since 0.5
	 * @return array Allowed tags.
	 */
	public static function get_allowed_tags() {
		return self::$allowed_tags;
	}

	/**
	 * Get allowed tag.
	 *
	 * Get the rules for a single tag so that the entire data structure needn't be passed around.
	 *
	 * @since 0.7
	 * @param string $node_name Tag name.
	 * @return array|null Allowed tag, or null if the tag does not exist.
	 */
	public static function get_allowed_tag( $node_name ) {
		if ( isset( self::$allowed_tags[ $node_name ] ) ) {
			return self::$allowed_tags[ $node_name ];
		}
		return null;
	}

	/**
	 * Get descendant tag lists.
	 *
	 * @since 1.1
	 * @return array Descendant tags list.
	 */
	public static function get_descendant_tag_lists() {
		return self::$descendant_tag_lists;
	}

	/**
	 * Get allowed descendant tag list for a tag.
	 *
	 * Get the descendant rules for a single tag so that the entire data structure needn't be passed around.
	 *
	 * @since 1.1
	 * @param string $name Name for the descendants list.
	 * @return array|bool Allowed tags list, or false if there are no restrictions.
	 */
	public static function get_descendant_tag_list( $name ) {
		if ( isset( self::$descendant_tag_lists[ $name ] ) ) {
			return self::$descendant_tag_lists[ $name ];
		}
		return false;
	}

	/**
	 * Get reference point spec.
	 *
	 * @since 1.0
	 * @param string $tag_spec_name Tag spec name.
	 * @return array|null Reference point spec, or null if does not exist.
	 */
	public static function get_reference_point_spec( $tag_spec_name ) {
		if ( isset( self::$reference_points[ $tag_spec_name ] ) ) {
			return self::$reference_points[ $tag_spec_name ];
		}
		return null;
	}

	/**
	 * Get list of globally-allowed attributes.
	 *
	 * @since 0.5
	 * @return array Allowed tag.
	 */
	public static function get_allowed_attributes() {
		return self::$globally_allowed_attrs;
	}

	/**
	 * Get layout attributes.
	 *
	 * @since 0.5
	 * @return array Allowed tag.
	 */
	public static function get_layout_attributes() {
		return self::$layout_allowed_attrs;
	}''')

	out.append('')

	out.append('}')
	out.append('')

	logging.info('... done')


def ParseRules(out_dir):
	logging.info('entering ...')

	# These imports happen late, within this method because they don't necessarily
	# exist when the module starts running, and the ones that probably do
	# are checked by CheckPrereqs.

	from google.protobuf import text_format
	validator_pb2 = imp.load_source('validator_pb2', os.path.join( out_dir, 'validator_pb2.py' ))

	allowed_tags = {}
	attr_lists = {}
	descendant_lists = {}
	reference_points = {}
	versions = {}

	specfile='%s/validator.protoascii' % out_dir

	validator_pb2=validator_pb2
	text_format=text_format

	# Merge specfile with message buffers.
	rules = validator_pb2.ValidatorRules()
	text_format.Merge(open(specfile).read(), rules)

	# Record the version of this specfile and the corresponding validator version.
	if rules.HasField('spec_file_revision'):
		versions['spec_file_revision'] = rules.spec_file_revision

	if rules.HasField('min_validator_revision_required'):
		versions['min_validator_revision_required'] = rules.min_validator_revision_required

	# Build a dictionary of the named attribute lists that are used by multiple tags.
	for (field_desc, field_val) in rules.ListFields():
		if 'attr_lists' == field_desc.name:
			for attr_spec in field_val:
				attr_lists[UnicodeEscape(attr_spec.name)] = GetAttrs(attr_spec.attrs)

	# Build a dictionary of allowed tags and an associated list of their allowed
	# attributes, values and other criteria.

	# Don't include tags that have a mandatory parent with one of these tag names
	# since we're only concerned with using this tag list to validate the HTML
	# of the DOM
	mandatory_parent_blacklist = [
		'$ROOT',
		'!DOCTYPE',
	]

	for (field_desc, field_val) in rules.ListFields():
		if 'tags' == field_desc.name:
			for tag_spec in field_val:

				# Ignore tags that are outside of the body
				if tag_spec.HasField('mandatory_parent') and tag_spec.mandatory_parent in mandatory_parent_blacklist and tag_spec.tag_name != 'HTML':
					continue

				# Ignore deprecated tags
				if tag_spec.HasField('deprecation'):
					continue

				# Handle the special $REFERENCE_POINT tag
				if '$REFERENCE_POINT' == tag_spec.tag_name:
					reference_points[ tag_spec.spec_name ] = GetTagSpec(tag_spec, attr_lists)
					continue

				# If we made it here, then start adding the tag_spec
				if tag_spec.tag_name.lower() not in allowed_tags:
					tag_list = []
				else:
					tag_list = allowed_tags[UnicodeEscape(tag_spec.tag_name).lower()]
				# AddTag(allowed_tags, tag_spec, attr_lists)

				gotten_tag_spec = GetTagSpec(tag_spec, attr_lists)
				if gotten_tag_spec is not None:
					tag_list.append(gotten_tag_spec)
					allowed_tags[UnicodeEscape(tag_spec.tag_name).lower()] = tag_list
		elif 'descendant_tag_list' == field_desc.name:
			for list in field_val:
				descendant_lists[list.name] = []
				for val in list.tag:
					descendant_lists[list.name].append( val.lower() )

	logging.info('... done')
	return allowed_tags, attr_lists, descendant_lists, reference_points, versions


def GetTagSpec(tag_spec, attr_lists):
	logging.info('entering ...')

	tag_dict = GetTagRules(tag_spec)
	if tag_dict is None:
		return None
	attr_dict = GetAttrs(tag_spec.attrs)

	# Now add attributes from any attribute lists to this tag.
	for (tag_field_desc, tag_field_val) in tag_spec.ListFields():
		if 'attr_lists' == tag_field_desc.name:
			for attr_list in tag_field_val:
				attr_dict.update(attr_lists[UnicodeEscape(attr_list)])

	logging.info('... done')
	tag_spec_dict = {'tag_spec':tag_dict, 'attr_spec_list':attr_dict}
	if tag_spec.HasField('cdata'):
		cdata_dict = {}
		for (field_descriptor, field_value) in tag_spec.cdata.ListFields():
			if isinstance(field_value, (unicode, str, bool, int)):
				cdata_dict[ field_descriptor.name ] = field_value
			elif hasattr( field_value, '_values' ):
				cdata_dict[ field_descriptor.name ] = {}
				for _value in field_value._values:
					for (key,val) in _value.ListFields():
						cdata_dict[ field_descriptor.name ][ key.name ] = val
			elif 'css_spec' == field_descriptor.name:
				css_spec = {}

				css_spec['allowed_at_rules'] = []
				for at_rule_spec in field_value.at_rule_spec:
					if '$DEFAULT' == at_rule_spec.name:
						continue
					css_spec['allowed_at_rules'].append( at_rule_spec.name )

				for css_spec_field_name in ( 'allowed_declarations', 'declaration', 'font_url_spec', 'image_url_spec', 'validate_keyframes' ):
					if not hasattr( field_value, css_spec_field_name ):
						continue
					css_spec_field_value = getattr( field_value, css_spec_field_name )
					if isinstance(css_spec_field_value, (list, collections.Sequence, google.protobuf.internal.containers.RepeatedScalarFieldContainer)):
						css_spec[ css_spec_field_name ] = [ val for val in css_spec_field_value ]
					elif hasattr( css_spec_field_value, 'ListFields' ):
						css_spec[ css_spec_field_name ] = {}
						for (css_spec_field_item_descriptor, css_spec_field_item_value) in getattr( field_value, css_spec_field_name ).ListFields():
							if isinstance(css_spec_field_item_value, (list, collections.Sequence, google.protobuf.internal.containers.RepeatedScalarFieldContainer)):
								css_spec[ css_spec_field_name ][ css_spec_field_item_descriptor.name ] = [ val for val in css_spec_field_item_value ]
							else:
								css_spec[ css_spec_field_name ][ css_spec_field_item_descriptor.name ] = css_spec_field_item_value
					else:
						css_spec[ css_spec_field_name ] = css_spec_field_value

				cdata_dict['css_spec'] = css_spec
		if len( cdata_dict ) > 0:
			tag_spec_dict['cdata'] = cdata_dict

	return tag_spec_dict


def GetTagRules(tag_spec):
	logging.info('entering ...')

	tag_rules = {}

	if hasattr(tag_spec, 'also_requires_tag') and tag_spec.also_requires_tag:
		also_requires_tag_list = []
		for also_requires_tag in tag_spec.also_requires_tag:
			also_requires_tag_list.append(UnicodeEscape(also_requires_tag))
		tag_rules['also_requires_tag'] = also_requires_tag_list

	if hasattr(tag_spec, 'requires_extension') and len( tag_spec.requires_extension ) != 0:
		requires_extension_list = []
		for requires_extension in tag_spec.requires_extension:
			requires_extension_list.append(requires_extension)
		tag_rules['requires_extension'] = requires_extension_list

	if hasattr(tag_spec, 'reference_points') and len( tag_spec.reference_points ) != 0:
		tag_reference_points = {}
		for reference_point_spec in tag_spec.reference_points:
			tag_reference_points[ reference_point_spec.tag_spec_name ] = {
				"mandatory": reference_point_spec.mandatory,
				"unique": reference_point_spec.unique
			}
		if len( tag_reference_points ) > 0:
			tag_rules['reference_points'] = tag_reference_points

	if hasattr(tag_spec, 'also_requires_tag_warning') and len( tag_spec.also_requires_tag_warning ) != 0:
		also_requires_tag_warning_list = []
		for also_requires_tag_warning in tag_spec.also_requires_tag_warning:
			also_requires_tag_warning_list.append(also_requires_tag_warning)
		tag_rules['also_requires_tag_warning'] = also_requires_tag_warning_list

	if tag_spec.disallowed_ancestor:
		disallowed_ancestor_list = []
		for disallowed_ancestor in tag_spec.disallowed_ancestor:
			disallowed_ancestor_list.append(UnicodeEscape(disallowed_ancestor).lower())
		tag_rules['disallowed_ancestor'] = disallowed_ancestor_list

	if tag_spec.html_format:
		html_format_list = []
		has_amp_format = False
		for html_format in tag_spec.html_format:
			if 1 == html_format:
				has_amp_format = True
		if not has_amp_format:
			return None

	if tag_spec.HasField('extension_spec'):
		extension_spec = {}
		for field in tag_spec.extension_spec.ListFields():
			if isinstance(field[1], (list, google.protobuf.internal.containers.RepeatedScalarFieldContainer,google.protobuf.pyext._message.RepeatedScalarContainer)):
				extension_spec[ field[0].name ] = []
				for val in field[1]:
					extension_spec[ field[0].name ].append( val )
			else:
				extension_spec[ field[0].name ] = field[1]
		tag_rules['extension_spec'] = extension_spec

	if tag_spec.HasField('mandatory'):
		tag_rules['mandatory'] = tag_spec.mandatory

	if tag_spec.HasField('mandatory_alternatives'):
		tag_rules['mandatory_alternatives'] = UnicodeEscape(tag_spec.mandatory_alternatives)

	if tag_spec.HasField('mandatory_ancestor'):
		tag_rules['mandatory_ancestor'] = UnicodeEscape(tag_spec.mandatory_ancestor).lower()

	if tag_spec.HasField('mandatory_ancestor_suggested_alternative'):
		tag_rules['mandatory_ancestor_suggested_alternative'] = UnicodeEscape(tag_spec.mandatory_ancestor_suggested_alternative).lower()

	if tag_spec.HasField('mandatory_parent'):
		tag_rules['mandatory_parent'] = UnicodeEscape(tag_spec.mandatory_parent).lower()

	if tag_spec.HasField('spec_name'):
		tag_rules['spec_name'] = UnicodeEscape(tag_spec.spec_name)

	if tag_spec.HasField('spec_url'):
		tag_rules['spec_url'] = UnicodeEscape(tag_spec.spec_url)

	if tag_spec.HasField('unique'):
		tag_rules['unique'] = tag_spec.unique

	if tag_spec.HasField('unique_warning'):
		tag_rules['unique_warning'] = tag_spec.unique_warning

	if tag_spec.HasField('child_tags'):
		child_tags = []
		for field in tag_spec.child_tags.ListFields():
			if isinstance(field[1], (list, google.protobuf.internal.containers.RepeatedScalarFieldContainer)):
				if 'child_tag_name_oneof' == field[0].name:
					for val in field[1]:
						child_tags.append( val.lower() )
		tag_rules['child_tags'] = child_tags

	if tag_spec.HasField('descendant_tag_list'):
		tag_rules['descendant_tag_list'] = tag_spec.descendant_tag_list

	if tag_spec.HasField('amp_layout'):
		amp_layout = {}
		for field in tag_spec.amp_layout.ListFields():
			if 'supported_layouts' == field[0].name:
				amp_layout['supported_layouts'] = [ val for val in field[1] ]
			else:
				amp_layout[ field[0].name ] = field[1]
		tag_rules['amp_layout'] = amp_layout

	logging.info('... done')
	return tag_rules


def GetAttrs(attrs):
	logging.info('entering ...')

	attr_dict = {}
	for attr_spec in attrs:

		value_dict = GetValues(attr_spec)

		# Add attribute name and alternative_names
		attr_dict[UnicodeEscape(attr_spec.name)] = value_dict

	logging.info('... done')
	return attr_dict


def GetValues(attr_spec):
	logging.info('entering ...')

	value_dict = {}

	# Add alternative names
	if attr_spec.alternative_names:
		alt_names_list = []
		for alternative_name in attr_spec.alternative_names:
			alt_names_list.append(UnicodeEscape(alternative_name))
		value_dict['alternative_names'] = alt_names_list

	# Add blacklisted value regex
	if attr_spec.HasField('blacklisted_value_regex'):
		value_dict['blacklisted_value_regex'] = attr_spec.blacklisted_value_regex

	# dispatch_key is an int
	if attr_spec.HasField('dispatch_key'):
		value_dict['dispatch_key'] = attr_spec.dispatch_key

	# mandatory is a boolean
	if attr_spec.HasField('mandatory'):
		value_dict['mandatory'] = attr_spec.mandatory

	# Add allowed value
	if attr_spec.value:
		value_dict['value'] = list( attr_spec.value )

	# value_casei
	if attr_spec.value_casei:
		value_dict['value_casei'] = list( attr_spec.value_casei )

	# value_regex
	if attr_spec.HasField('value_regex'):
		value_dict['value_regex'] = attr_spec.value_regex

	# value_regex_casei
	if attr_spec.HasField('value_regex_casei'):
		value_dict['value_regex_casei'] = attr_spec.value_regex_casei

	#value_properties is a dictionary of dictionaries
	if attr_spec.HasField('value_properties'):
		value_properties_dict = {}
		for (value_properties_key, value_properties_val) in attr_spec.value_properties.ListFields():
			for value_property in value_properties_val:
				property_dict = {}
				# print 'value_property.name: %s' % value_property.name
				for (key,val) in value_property.ListFields():
					if val != value_property.name:
						if isinstance(val, unicode):
							val = UnicodeEscape(val)
						property_dict[UnicodeEscape(key.name)] = val
				value_properties_dict[UnicodeEscape(value_property.name)] = property_dict
		value_dict['value_properties'] = value_properties_dict

	# value_url is a dictionary
	if attr_spec.HasField('value_url'):
		value_url_dict = {}
		for (value_url_key, value_url_val) in attr_spec.value_url.ListFields():
			if isinstance(value_url_val, (list, collections.Sequence, google.protobuf.internal.containers.RepeatedScalarFieldContainer)):
				value_url_val_val = []
				for val in value_url_val:
					value_url_val_val.append(UnicodeEscape(val))
			else:
				value_url_val_val = value_url_val
			value_url_dict[value_url_key.name] = value_url_val_val
		value_dict['value_url'] = value_url_dict

	logging.info('... done')
	return value_dict


def UnicodeEscape(string):
	"""Helper function which escapes unicode characters.

	Args:
		string: A string which may contain unicode characters.
	Returns:
		An escaped string.
	"""
	return ('' + string).encode('unicode-escape')

def Phpize(data, indent=0):
	"""Helper function to convert JSON-serializable data into PHP literals.

	Args:
		data: Any JSON-serializable.
	Returns:
		String formatted as PHP literal.
	"""
	json_string = json.dumps(data, sort_keys=True, ensure_ascii=False)

	pipe = subprocess.Popen(['php', '-r', 'var_export( json_decode( file_get_contents( "php://stdin" ), true ) );'], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
	php_stdout = pipe.communicate(input=json_string)[0]
	php_exported = php_stdout.decode()

	# Clean up formatting.
	# TODO: Just use PHPCBF for this.
	php_exported = re.sub( r'^ +', lambda match: ( len(match.group(0))/2 ) * '\t', php_exported, flags=re.MULTILINE )
	php_exported = php_exported.replace( 'array (', 'array(' )
	php_exported = re.sub( r' => \n\s+', ' => ', php_exported, flags=re.MULTILINE )
	php_exported = re.sub( r'^(\s+)\d+ =>\s*', r'\1', php_exported, flags=re.MULTILINE )

	# Add additional indents.
	if indent > 0:
		php_exported = re.sub( r'^', '\t' * indent, php_exported, flags=re.MULTILINE )
	return php_exported

def Main( validator_directory, out_dir ):
	"""The main method, which executes all build steps and runs the tests."""
	logging.basicConfig(format='[[%(filename)s %(funcName)s]] - %(message)s', level=logging.INFO)

	validator_directory = os.path.realpath(validator_directory)
	out_dir = os.path.realpath(out_dir)

	SetupOutDir(out_dir)
	GenValidatorProtoascii(validator_directory, out_dir)
	GenValidatorPb2Py(validator_directory, out_dir)
	GenValidatorProtoascii(validator_directory,out_dir)
	GeneratePHP(out_dir)

if __name__ == '__main__':
	project_repo_absolute_path = os.path.realpath( os.path.join( os.path.dirname( __file__ ), '..' ) )
	validator_directory = os.path.join( project_repo_absolute_path, 'vendor/ampproject/amphtml/validator' )
	out_dir = os.path.join( tempfile.gettempdir(), 'amp_wp' )
	Main( validator_directory, out_dir )
