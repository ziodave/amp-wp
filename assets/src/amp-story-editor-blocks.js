/**
 * WordPress dependencies
 */
import { addFilter } from '@wordpress/hooks';
import domReady from '@wordpress/dom-ready';
import { select, subscribe, dispatch } from '@wordpress/data';
import { getDefaultBlockName, setDefaultBlockName, getBlockTypes, unregisterBlockType } from '@wordpress/blocks';

/**
 * Internal dependencies
 */
import {
	withAmpStorySettings,
	withAnimationControls,
	withPageNumber,
	withWrapperProps,
	withActivePageState,
} from './components';
import { ALLOWED_BLOCKS } from './constants';
import {
	maybeEnqueueFontStyle,
	setBlockParent,
	addAMPAttributes,
	addAMPExtraProps,
	disableBlockDropZone,
	getTotalAnimationDuration,
	renderStoryComponents,
} from './helpers';
import store from './stores/amp-story';

const {
	getSelectedBlockClientId,
	getBlocksByClientId,
	getClientIdsWithDescendants,
	getBlockRootClientId,
	getBlockOrder,
	getBlock,
	getBlockAttributes,
} = select( 'core/editor' );

const {
	isReordering,
	getBlockOrder: getCustomBlockOrder,
	getAnimatedBlocks,
} = select( 'amp/story' );

const {
	moveBlockToPosition,
	updateBlockAttributes,
} = dispatch( 'core/editor' );

const {
	setCurrentPage,
	removePage,
	addAnimation,
	changeAnimationType,
	changeAnimationDuration,
	changeAnimationDelay,
} = dispatch( 'amp/story' );

/**
 * Initialize editor integration.
 */
domReady( () => {
	// Ensure that the default block is page when no block is selected.
	setDefaultBlockName( 'amp/amp-story-page' );

	// Remove all blocks that aren't whitelisted.
	const disallowedBlockTypes = getBlockTypes().filter( ( { name } ) => ! ALLOWED_BLOCKS.includes( name ) );

	for ( const blockType of disallowedBlockTypes ) {
		unregisterBlockType( blockType.name );
	}

	const allBlocks = getBlocksByClientId( getClientIdsWithDescendants() );

	// Set initially shown page.
	const firstPage = allBlocks.find( ( { name } ) => name === 'amp/amp-story-page' );
	setCurrentPage( firstPage ? firstPage.clientId : undefined );

	// Set initial animation order state for all child blocks.
	for ( const block of allBlocks ) {
		const page = getBlockRootClientId( block.clientId );

		if ( page ) {
			const { ampAnimationType, ampAnimationAfter, ampAnimationDuration, ampAnimationDelay } = block.attributes;
			const predecessor = allBlocks.find( ( b ) => b.attributes.anchor === ampAnimationAfter );

			addAnimation( page, block.clientId, predecessor ? predecessor.clientId : undefined );

			changeAnimationType( page, block.clientId, ampAnimationType );
			changeAnimationDuration( page, block.clientId, ampAnimationDuration ? parseInt( ampAnimationDuration.replace( 'ms', '' ) ) : undefined );
			changeAnimationDelay( page, block.clientId, ampAnimationDelay ? parseInt( ampAnimationDelay.replace( 'ms', '' ) ) : undefined );
		}

		// Load all needed fonts.
		if ( block.attributes.ampFontFamily ) {
			maybeEnqueueFontStyle( block.attributes.ampFontFamily );
		}
	}

	renderStoryComponents();

	// Prevent WritingFlow component from focusing on last text field when clicking below the carousel.
	document.querySelector( '.editor-writing-flow__click-redirect' ).remove();
} );

let blockOrder = getBlockOrder();

subscribe( () => {
	const defaultBlockName = getDefaultBlockName();
	const selectedBlockClientId = getSelectedBlockClientId();

	// Switch default block depending on context
	if ( selectedBlockClientId ) {
		const selectedBlock = getBlock( selectedBlockClientId );

		if ( 'amp/amp-story-page' === selectedBlock.name && 'amp/amp-story-page' !== defaultBlockName ) {
			setDefaultBlockName( 'amp/amp-story-page' );
		} else if ( 'amp/amp-story-page' !== selectedBlock.name && 'amp/amp-story-text' !== defaultBlockName ) {
			setDefaultBlockName( 'amp/amp-story-text' );
		}
	} else if ( ! selectedBlockClientId && 'amp/amp-story-page' !== defaultBlockName ) {
		setDefaultBlockName( 'amp/amp-story-page' );
	}

	const newBlockOrder = getBlockOrder();
	const deletedPages = blockOrder.filter( ( block ) => ! newBlockOrder.includes( block ) );
	const newlyAddedPages = newBlockOrder.find( ( block ) => ! blockOrder.includes( block ) );

	blockOrder = newBlockOrder;

	// If a new page has been inserted, make it the current one.
	if ( newlyAddedPages ) {
		setCurrentPage( newlyAddedPages );
	}

	// Remove stale data from store.
	for ( const oldPage of deletedPages ) {
		removePage( oldPage );
	}
} );

store.subscribe( () => {
	const editorBlockOrder = getBlockOrder();
	const customBlockOrder = getCustomBlockOrder();

	// The block order has changed, let's re-order.
	if ( ! isReordering() && customBlockOrder.length > 0 && editorBlockOrder !== customBlockOrder ) {
		for ( const [ index, page ] of customBlockOrder.entries() ) {
			moveBlockToPosition( page, '', '', index );
		}
	}

	const animatedBlocks = getAnimatedBlocks();

	// Update pages and blocks based on updated animation data.
	for ( const page in animatedBlocks ) {
		if ( ! animatedBlocks.hasOwnProperty( page ) ) {
			continue;
		}

		const pageAttributes = getBlockAttributes( page );

		const animatedBlocksPerPage = animatedBlocks[ page ].filter( ( { id } ) => page === getBlockRootClientId( id ) );

		if ( 'auto' === pageAttributes.autoAdvanceAfter ) {
			const totalAnimationDuration = getTotalAnimationDuration( animatedBlocksPerPage );
			const totalAnimationDurationInSeconds = Math.ceil( totalAnimationDuration / 1000 );

			if ( totalAnimationDurationInSeconds !== pageAttributes.autoAdvanceAfterDuration ) {
				updateBlockAttributes( page, { autoAdvanceAfterDuration: totalAnimationDurationInSeconds } );
			}
		}

		for ( const item of animatedBlocksPerPage ) {
			const { id, parent, animationType, duration, delay } = item;

			const parentBlock = parent ? getBlock( parent ) : undefined;

			updateBlockAttributes( id, {
				ampAnimationAfter: parentBlock ? parentBlock.attributes.anchor : undefined,
				ampAnimationType: animationType,
				ampAnimationDuration: duration,
				ampAnimationDelay: delay,
			} );
		}
	}
} );

addFilter( 'blocks.registerBlockType', 'ampStoryEditorBlocks/setBlockParent', setBlockParent );
addFilter( 'blocks.registerBlockType', 'ampStoryEditorBlocks/addAttributes', addAMPAttributes );
addFilter( 'editor.BlockEdit', 'ampStoryEditorBlocks/addAnimationControls', withAnimationControls );
addFilter( 'editor.BlockEdit', 'ampStoryEditorBlocks/addStorySettings', withAmpStorySettings );
addFilter( 'editor.BlockEdit', 'ampStoryEditorBlocks/addPageNumber', withPageNumber );
addFilter( 'editor.BlockListBlock', 'ampStoryEditorBlocks/withActivePageState', withActivePageState );
addFilter( 'editor.BlockListBlock', 'ampStoryEditorBlocks/addWrapperProps', withWrapperProps );
addFilter( 'blocks.getSaveContent.extraProps', 'ampStoryEditorBlocks/addExtraAttributes', addAMPExtraProps );
addFilter( 'editor.BlockDropZone', 'ampStoryEditorBlocks/disableBlockDropZone', disableBlockDropZone );