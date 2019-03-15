/**
 * WordPress dependencies
 */
import { select, combineReducers } from '@wordpress/data';

const { getBlock, getBlockOrder, getAdjacentBlockClientId } = select( 'core/editor' );

/**
 * Reducer handling animation state changes.
 *
 * For each page, its animated elements with their
 * data (ID, duration, delay, predecessor) are stored.
 *
 * @param {Object} state  Current state.
 * @param {Object} action Dispatched action.
 *
 * @return {Object} Updated state.
 */
export function animations( state = {}, action ) {
	const newAnimationOrder = { ...state };
	const { page, item, predecessor, animationType, duration, delay } = action;
	const pageAnimationOrder = newAnimationOrder[ page ] || [];

	const entryIndex = ( entry ) => pageAnimationOrder.findIndex( ( { id } ) => id === entry );

	switch ( action.type ) {
		case 'ADD_ANIMATION':
			const hasCycle = ( a, b ) => {
				let parent = b;

				while ( parent !== undefined ) {
					if ( parent === a ) {
						return true;
					}

					const parentItem = pageAnimationOrder.find( ( { id } ) => id === parent );
					parent = parentItem ? parentItem.parent : undefined;
				}

				return false;
			};

			const parent = -1 !== entryIndex( predecessor ) && ! hasCycle( item, predecessor ) ? predecessor : undefined;

			if ( entryIndex( item ) !== -1 ) {
				pageAnimationOrder[ entryIndex( item ) ].parent = parent;
			} else {
				pageAnimationOrder.push( { id: item, parent } );
			}

			return {
				...newAnimationOrder,
				[ page ]: pageAnimationOrder,
			};

		case 'CHANGE_ANIMATION_TYPE':
			// Animation was disabled, update all successors.
			if ( ! animationType ) {
				if ( entryIndex( item ) !== -1 ) {
					const itemPredecessor = pageAnimationOrder[ entryIndex( item ) ].parent;

					for ( const successor in pageAnimationOrder.filter( ( { parent: p } ) => p === item ) ) {
						pageAnimationOrder[ successor ].parent = itemPredecessor.parent;
					}

					pageAnimationOrder.splice( entryIndex( item ), 1 );
				}
			} else if ( entryIndex( item ) !== -1 ) {
				pageAnimationOrder[ entryIndex( item ) ].animationType = animationType;
			} else {
				pageAnimationOrder.push( { id: item, animationType } );
			}

			return {
				...newAnimationOrder,
				[ page ]: pageAnimationOrder,
			};

		case 'CHANGE_ANIMATION_DURATION':
			if ( entryIndex( item ) !== -1 ) {
				pageAnimationOrder[ entryIndex( item ) ].duration = duration;
			}

			return {
				...newAnimationOrder,
				[ page ]: pageAnimationOrder,
			};

		case 'CHANGE_ANIMATION_DELAY':
			if ( entryIndex( item ) !== -1 ) {
				pageAnimationOrder[ entryIndex( item ) ].delay = delay;
			}

			return {
				...newAnimationOrder,
				[ page ]: pageAnimationOrder,
			};
	}

	return state;
}

/**
 * Reducer handling changes to the current page.
 *
 * @param {Object} state  Current state.
 * @param {Object} action Dispatched action.
 *
 * @return {Object} Updated state.
 */
export function currentPage( state = undefined, action ) {
	const { page } = action;

	switch ( action.type ) {
		case 'REMOVE_PAGE':
			if ( page === state ) {
				return getAdjacentBlockClientId( page, -1 ) || getAdjacentBlockClientId( page, 1 ) || ( getBlockOrder() ? [ 0 ] : getBlockOrder() ) || undefined;
			}

			return state;
		case 'SET_CURRENT_PAGE':
			return getBlock( page ) ? page : state;
	}

	return state;
}

/**
 * Reducer handling block order.
 *
 * @param {Object} state  Current state.
 * @param {Object} action Dispatched action.
 *
 * @return {Object} Updated state.
 */
export function blocks( state = {}, action ) {
	switch ( action.type ) {
		case 'START_REORDERING':
			return {
				...state,
				order: getBlockOrder(),
				isReordering: true,
			};

		case 'STOP_REORDERING':
			return {
				...state,
				isReordering: false,
			};

		case 'MOVE_PAGE':
			const { page, index } = action;

			const oldIndex = state.order.indexOf( page );
			const newBlockOrder = [ ...state.order ];
			newBlockOrder.splice( index, 0, ...newBlockOrder.splice( oldIndex, 1 ) );

			return {
				...state,
				order: newBlockOrder,
			};

		case 'RESET_ORDER':
			return {
				...state,
				order: getBlockOrder(),
				isReordering: false,
			};
	}

	return state;
}

export default combineReducers( { animations, currentPage, blocks } );